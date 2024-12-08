import streamlit as st
import pandas as pd
import time
import random
from io import BytesIO
import os
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from yt_dlp import YoutubeDL
from fake_useragent import UserAgent
from typing import Optional
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Custom styling
st.markdown("""
    <style>
        .title-container {
            display: flex;
            align-items: center;
            margin-bottom: 2rem;
        }
        .logo-img {
            margin-right: 1rem;
        }
    </style>
""", unsafe_allow_html=True)

# Create two columns for logo and title
col1, col2 = st.columns([1, 4])

# Display logo in first column
with col1:
    logo_path = Path(__file__).parent / "logo.png"
    if logo_path.exists():
        st.image(str(logo_path), width=100)

# Display title in second column
with col2:
    st.title("Mirchi Playlist Tracker")

# Initialize UserAgent for rotating user agents
ua = UserAgent()

def get_random_user_agent():
    return ua.random

def random_delay():
    time.sleep(random.uniform(1, 5))

def retry_with_backoff(func, max_retries=3, backoff_factor=2):
    def wrapper(*args, **kwargs):
        retries = 0
        while retries < max_retries:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                wait = backoff_factor ** retries
                st.warning(f"Request failed. Retrying in {wait} seconds...")
                time.sleep(wait)
                retries += 1
        raise Exception("Max retries reached. Unable to complete request.")
    return wrapper

def setup_selenium():
    """Setup Selenium WebDriver"""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def scrape_playcount(url: str, driver) -> int:
    """Scrape play count from Spotify URL"""
    try:
        driver.get(url)
        play_count_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR, 
                "span.encore-text-body-small[data-testid='playcount']"
            ))
        )
        count_text = ''.join(filter(str.isdigit, play_count_element.text))
        return int(count_text) if count_text else 0
    except Exception as e:
        st.error(f"Error scraping {url}: {str(e)}")
        return 0

@retry_with_backoff
def get_youtube_views(video_url):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        random_delay()
        return info.get('view_count', 0)

def get_spotify_url_column(df: pd.DataFrame) -> Optional[str]:
    """Find the Spotify URL column using common variations of the name"""
    possible_names = ['Spotify URL', 'Spotify Link', 'spotify_url', 'spotify url', 'URL']
    for name in possible_names:
        if name in df.columns:
            return name
    return None

def process_spotify_data(df: pd.DataFrame, spotify_url_column: str) -> pd.DataFrame:
    """Process Spotify data and add play counts"""
    df = df.copy()
    play_counts = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        driver = setup_selenium()
        total_rows = len(df)
        
        for index, row in df.iterrows():
            # Update progress
            progress = (index + 1) / total_rows
            progress_bar.progress(progress)
            status_text.text(f"Processing row {index + 1} of {total_rows}")
            
            spotify_url = row[spotify_url_column]
            if pd.isna(spotify_url):
                play_counts.append(0)
                continue
            
            # Get play count
            play_count = scrape_playcount(spotify_url, driver)
            play_counts.append(play_count)
            
            # Add small delay to avoid rate limiting
            time.sleep(1)
        
        # Add play counts to DataFrame
        df['Play Count'] = play_counts
        return df
        
    except Exception as e:
        st.error(f"Error processing data: {str(e)}")
        return df
    finally:
        if 'driver' in locals():
            driver.quit()
        progress_bar.empty()
        status_text.empty()

def format_views_to_millions(views):
    """Convert views to millions format"""
    if pd.isna(views):
        return None
    views = float(views)
    millions = views / 1_000_000
    if millions < 1:
        return round(millions, 2)  # Use decimals only for < 1M
    return int(millions)  # No decimals for >= 1M

def process_youtube_data(df: pd.DataFrame, youtube_url_column: str) -> pd.DataFrame:
    """Process YouTube data with progress tracking"""
    df = df.copy()
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        total_rows = len(df)
        views = []
        
        for index, row in df.iterrows():
            progress = (index + 1) / total_rows
            progress_bar.progress(progress)
            status_text.text(f"Processing YouTube row {index + 1} of {total_rows}")
            
            youtube_url = row[youtube_url_column]
            if pd.isna(youtube_url):
                views.append(None)
                continue
                
            try:
                view_count = get_youtube_views(youtube_url)
                views_in_millions = format_views_to_millions(view_count)
                views.append(views_in_millions)
            except Exception as e:
                st.error(f"Error processing URL {youtube_url}: {str(e)}")
                views.append(None)
            
            time.sleep(1)
            
        df['Views (Millions)'] = views
        return df
        
    finally:
        progress_bar.empty()
        status_text.empty()

# Initialize session state
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'spotify_url_column' not in st.session_state:
    st.session_state.spotify_url_column = None
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = None

uploaded_file = st.file_uploader("Upload Excel file", type="xlsx")

if uploaded_file:
    excel_file = pd.ExcelFile(uploaded_file)
    sheet_names = excel_file.sheet_names
    
    spotify_sheet = st.selectbox("Select Spotify data sheet", sheet_names)
    youtube_sheet = st.selectbox("Select YouTube data sheet", sheet_names)
    
    if st.button("Load Data"):
        spotify_df = pd.read_excel(excel_file, sheet_name=spotify_sheet)
        youtube_df = pd.read_excel(excel_file, sheet_name=youtube_sheet)
        
        st.session_state['spotify_df'] = spotify_df
        st.session_state['youtube_df'] = youtube_df
        
        # Reset column selection
        st.session_state.spotify_url_column = None
        st.session_state.processed_data = None
        
        st.success("Data loaded successfully!")

    col1, col2 = st.columns(2)

    with col1:
        if 'spotify_df' in st.session_state:
            spotify_url_column = st.selectbox(
                "Select Spotify URL column",
                options=st.session_state.spotify_df.columns,
                key='spotify_url_select'
            )
            
            if st.button("Process Data", key='process_button'):
                st.session_state.processing = True
                st.session_state.spotify_url_column = spotify_url_column
                
                with st.spinner("Processing Spotify data..."):
                    updated_df = process_spotify_data(
                        st.session_state.spotify_df,
                        st.session_state.spotify_url_column
                    )
                    st.session_state.processed_data = updated_df
                
                st.success("Processing complete!")
                st.write("Updated data:")
                st.dataframe(updated_df)
                
                # Download button
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    updated_df.to_excel(writer, sheet_name='Spotify Data', index=False)
                    st.session_state.youtube_df.to_excel(writer, sheet_name='YouTube Data', index=False)
                
                st.download_button(
                    label="Download Updated Excel",
                    data=output.getvalue(),
                    file_name="updated_playlist_data.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

    with col2:
        if 'youtube_df' in st.session_state:
            youtube_url_column = st.selectbox(
                "Select YouTube URL column",
                options=st.session_state.youtube_df.columns,
                key='youtube_url_select'
            )
            
            if st.button("Process YouTube Data", key='process_youtube'):
                if youtube_url_column:
                    with st.spinner("Processing YouTube data..."):
                        updated_df = process_youtube_data(
                            st.session_state.youtube_df,
                            youtube_url_column
                        )
                        st.session_state.youtube_df = updated_df
                        
                        if 'Views (Millions)' in updated_df.columns:
                            st.success("YouTube processing complete!")
                            st.write("Updated YouTube data:")
                            st.dataframe(updated_df)
                            
                            # Show bar chart of views
                            if len(updated_df) > 0:
                                st.bar_chart(updated_df.set_index(youtube_url_column)['Views (Millions)'])
                else:
                    st.error("Please select YouTube URL column")

    if 'spotify_df' in st.session_state and 'youtube_df' in st.session_state:
        if st.button("Process Data"):
            with st.spinner("Processing Spotify data..."):
                updated_spotify_df = process_spotify_data(st.session_state['spotify_df'])
                st.session_state['spotify_df'] = updated_spotify_df
                
            # Show download button only if processing is complete
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                st.session_state['spotify_df'].to_excel(writer, sheet_name='Spotify Data', index=False)
                st.session_state['youtube_df'].to_excel(writer, sheet_name='YouTube Data', index=False)
            output.seek(0)
            
            st.download_button(
                label="Download Updated Excel",
                data=output,
                file_name="updated_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

st.markdown("### Export Options")
    
col1, col2 = st.columns(2)

with col1:
    if st.button("Export Spotify Data"):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            st.session_state['spotify_df'].to_excel(writer, index=False)
        
        st.download_button(
            label="Download Spotify Data",
            data=output.getvalue(),
            file_name="spotify_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

with col2:
    if st.button("Export YouTube Data"):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            st.session_state['youtube_df'].to_excel(writer, index=False)
        
        st.download_button(
            label="Download YouTube Data",
            data=output.getvalue(),
            file_name="youtube_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

if st.button("Export Combined Data"):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        st.session_state['spotify_df'].to_excel(writer, sheet_name='Spotify Data', index=False)
        st.session_state['youtube_df'].to_excel(writer, sheet_name='YouTube Data', index=False)
    
    st.download_button(
        label="Download Combined Data",
        data=output.getvalue(),
        file_name="combined_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

st.write("""
### Usage Instructions:
1. Upload an Excel file with separate sheets for Spotify and YouTube data
2. Select the appropriate sheets
3. Select the column containing Spotify URLs
4. Click 'Process Data' to fetch play counts
5. Download the updated Excel file
""")

# Footer
st.markdown("---")
st.write("© ENIL. All rights reserved.")
