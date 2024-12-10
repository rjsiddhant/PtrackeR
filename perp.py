import streamlit as st
import pandas as pd
import time
import random
from io import BytesIO
from datetime import datetime
from yt_dlp import YoutubeDL
from typing import Optional
from playwright.sync_api import sync_playwright, TimeoutError

# Constants
MAX_RETRIES = 5
RATE_LIMIT = 3
XPATH_SELECTOR = "/html/body/div[6]/div/div[2]/div[4]/div/div[2]/div[2]/div/main/section/div[1]/div[3]/div[3]/div/span[8]"
CSS_SELECTOR = "span[data-testid='playcount']"

def get_spotify_data(url: str) -> int:
    """Scrape play count from Spotify URL using Playwright"""
    try:
        for attempt in range(MAX_RETRIES):
            try:
                time.sleep(RATE_LIMIT)
                with sync_playwright() as p:
                    browser = p.firefox.launch(headless=True)
                    context = browser.new_context()
                    page = context.new_page()
                    page.goto(url, wait_until='networkidle', timeout=60000)
                    
                    # Try both selectors
                    for selector in [f"xpath={XPATH_SELECTOR}", CSS_SELECTOR]:
                        try:
                            element = page.wait_for_selector(selector, timeout=10000)
                            if element:
                                count_text = ''.join(filter(str.isdigit, element.inner_text()))
                                browser.close()
                                return int(count_text) if count_text else 0
                        except:
                            continue
                    
                    st.warning(f"Play count element not found for URL: {url}")
                    browser.close()
                    return 0
                    
            except Exception as e:
                if attempt == MAX_RETRIES - 1:
                    st.error(f"Error fetching play count from {url}: {str(e)}")
                time.sleep(random.uniform(2, 5))
        return 0
    except Exception as e:
        st.error(f"Error in get_spotify_data: {str(e)}")
        return 0

def process_spotify_data(df: pd.DataFrame, spotify_url_column: str) -> pd.DataFrame:
    """Process Spotify data and add play counts"""
    df = df.copy()
    play_counts = []

    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        total_rows = len(df)

        for index, row in df.iterrows():
            progress = (index + 1) / total_rows
            progress_bar.progress(progress)
            status_text.text(f"Processing row {index + 1} of {total_rows}")

            spotify_url = row[spotify_url_column]
            if pd.isna(spotify_url):
                play_counts.append(0)
                continue

            # Get play count
            play_count = get_spotify_data(spotify_url)
            play_counts.append(play_count)

            # Add small delay to avoid rate limiting
            time.sleep(random.uniform(1, 3))

        # Add play counts to DataFrame
        df[f'Play Count ({datetime.now().date()})'] = play_counts
        return df

    except Exception as e:
        st.error(f"Error processing Spotify data: {str(e)}")
        return df
    finally:
        progress_bar.empty()
        status_text.empty()

def get_youtube_views(video_url: str) -> Optional[float]:
    """Get view count from YouTube URL using yt-dlp"""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
        }
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            view_count = info.get('view_count', 0)
            if view_count >= 1_000_000:
                return round(view_count / 1_000_000, 1)
            else:
                return round(view_count / 1_000_000, 2)
    except Exception as e:
        st.error(f"Error getting YouTube views for {video_url}: {str(e)}")
        return None

def process_youtube_data(df: pd.DataFrame, youtube_url_column: str) -> pd.DataFrame:
    """Process YouTube data and add view counts"""
    df = df.copy()
    views = []

    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        total_rows = len(df)

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
                views.append(view_count)
            except Exception as e:
                st.error(f"Error processing URL {youtube_url}: {str(e)}")
                views.append(None)

            time.sleep(random.uniform(1, 3))

        # Add view counts to DataFrame
        df[f'View Count ({datetime.now().date()})'] = views
        return df

    finally:
        progress_bar.empty()
        status_text.empty()

# Streamlit app
st.title("Spotify and YouTube Data Scraper")

# File upload section
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
        st.success("Data loaded successfully!")

    # Create two columns for processing
    col1, col2 = st.columns(2)

    with col1:
        if 'spotify_df' in st.session_state:
            spotify_url_column = st.selectbox(
                "Select Spotify URL column",
                options=st.session_state.spotify_df.columns,
                key='spotify_url_select'
            )

            if st.button("Process Spotify Data", key='process_spotify'):
                with st.spinner("Processing Spotify data..."):
                    updated_df = process_spotify_data(
                        st.session_state.spotify_df,
                        spotify_url_column
                    )
                    st.session_state.spotify_df = updated_df
                    st.success("Spotify processing complete!")
                    st.write("Updated Spotify data:")
                    st.dataframe(st.session_state.spotify_df)

    with col2:
        if 'youtube_df' in st.session_state:
            youtube_url_column = st.selectbox(
                "Select YouTube URL column",
                options=st.session_state.youtube_df.columns,
                key='youtube_url_select'
            )

            if st.button("Process YouTube Data", key='process_youtube'):
                with st.spinner("Processing YouTube data..."):
                    updated_df = process_youtube_data(
                        st.session_state.youtube_df,
                        youtube_url_column
                    )
                    st.session_state.youtube_df = updated_df
                    st.success("YouTube processing complete!")
                    st.write("Updated YouTube data:")
                    st.dataframe(st.session_state.youtube_df)

    # Export section
    st.markdown("### Export Options")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Export Spotify Data") and 'spotify_df' in st.session_state:
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                st.session_state.spotify_df.to_excel(writer, index=False)

            st.download_button(
                label="Download Spotify Data",
                data=output.getvalue(),
                file_name="spotify_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    with col2:
        if st.button("Export YouTube Data") and 'youtube_df' in st.session_state:
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                st.session_state.youtube_df.to_excel(writer, index=False)

            st.download_button(
                label="Download YouTube Data",
                data=output.getvalue(),
                file_name="youtube_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    with col3:
        if st.button("Export Combined Data") and all(df in st.session_state for df in ['spotify_df', 'youtube_df']):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                st.session_state.spotify_df.to_excel(writer, sheet_name='Spotify Data', index=False)
                st.session_state.youtube_df.to_excel(writer, sheet_name='YouTube Data', index=False)

            st.download_button(
                label="Download Combined Data",
                data=output.getvalue(),
                file_name="combined_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
