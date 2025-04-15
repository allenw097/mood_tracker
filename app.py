import streamlit as st
import gspread
import pandas as pd
import matplotlib.pyplot as plt
from google.oauth2.service_account import Credentials
from datetime import datetime, date

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

#-----------Set Up Google Sheets Access-----------


try:
    service_account_info = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES) 
    client = gspread.authorize(creds)
    sheet = client.open(st.secrets["sheet"]["name"]).sheet1
except Exception as e:
    st.error("Error connecting to Google Sheets. Make sure your credentials are configured correctly.")
    st.stop()


#----------- Helper Functions for Interacting with Sheet -----------


def record_mood(mood_icon, additional_comment=""):
    """Record a mood entry onto the sheet with the current timestamp, emoji, and an optional note."""
    timestamp_value = datetime.now().isoformat()
    try:
        sheet.append_row([timestamp_value, mood_icon, additional_comment])
    except Exception as ex:
        st.error(f"Error recording mood: {ex}")

def retrieve_moods():
    """Get all mood entries from the sheet and return them as a pandas DataFrame."""
    try:
        entries = sheet.get_all_records()
    except Exception as ex:
        st.error(f"Error retrieving data: {ex}")
        return pd.DataFrame()
    
    if not entries:
        return pd.DataFrame(columns=["timestamp", "mood", "note"])
    
    df_entries = pd.DataFrame(entries)
    df_entries['timestamp'] = pd.to_datetime(df_entries['timestamp'], errors='coerce')
    return df_entries


#----------- Streamlit UI -----------


st.title("Mood of the Queue")
st.write("Record the current vibe of the support ticket queue.")

# ----- Mood Entry Section -----
#Users can pick an emoji and optionally include a text note.

emoji_choices = ["😊", "😠", "😕", "🎉"]
chosen_emoji = st.selectbox("Select an emoji to represent the current mood:", emoji_choices)
comment_text = st.text_input("Add a short note (optional):", "e.g. lots of Rx delays today")

if st.button("Submit Entry"):
    record_mood(chosen_emoji, comment_text)
    st.success("Mood entry submitted!")


# ----- Add Auto-Refresh -----


from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=60000, key="mood_refresh")


# ----- Visualization Section With Filters -----


mood_data = retrieve_moods() #Get all the records from the sheet

if mood_data.empty: 
    st.info("No mood data available yet.")
else:
    #Create a 'date' column for grouping by day
    mood_data['date'] = mood_data['timestamp'].dt.date 

    # --- Sidebar Filtering Options ---
    st.sidebar.header("Filter Options")

    #Filter to allow selection of moods
    unique_moods = mood_data['mood'].unique().tolist()
    selected_moods = st.sidebar.multiselect("Select Moods", options=unique_moods, default=None)
    
    #Option to group results by day
    group_by_day = st.sidebar.checkbox("Group by Day", value=False)
    
    #Filter the data based on the selected moods
    filtered_data = mood_data[mood_data['mood'].isin(selected_moods)]
    
    #If the user doesn't select a filter
    if filtered_data.empty:
        st.header("Today's Mood Trends") #We output the default header of today's mood trends
        today_entries = mood_data[mood_data['timestamp'].dt.date == date.today()] #We only want the moods that were submitted today
        emoji_summary = today_entries['mood'].value_counts().sort_index() #Count the number of emojis
        fig, chart_ax = plt.subplots() #Create a plot
        emoji_summary.plot(kind="bar", ax=chart_ax, color="skyblue") 
        chart_ax.set_title("Mood Frequency for Today")
        chart_ax.set_xlabel("Mood")
        chart_ax.set_ylabel("Count")
        st.pyplot(fig)
    else:
        st.header("Filtered Mood Data") #create a header if user selected a filter
        
        #If user selects the Group by Day checkbox
        if group_by_day:
            #Group the filtered data by date and emoji counts
            grouped_data = filtered_data.groupby(['date', 'mood']).size().unstack(fill_value=0)
            st.write("### Grouped Mood Counts by Day")
            
            #Plot a bar chart for the grouped data
            fig, ax = plt.subplots()
            grouped_data.plot(kind="bar", ax=ax)
            ax.set_title("Mood Frequency by Day")
            ax.set_xlabel("Date")
            ax.set_ylabel("Count")
            st.pyplot(fig)
        else:
            #Overall mood counts without grouping by day
            overall_counts = filtered_data['mood'].value_counts().sort_index()
            st.write("### Overall Mood Counts")
            
            #Plot a bar chart of overall mood counts
            fig, ax = plt.subplots()
            overall_counts.plot(kind="bar", ax=ax, color="skyblue")
            ax.set_title("Overall Mood Frequency")
            ax.set_xlabel("Mood")
            ax.set_ylabel("Count")
            st.pyplot(fig)