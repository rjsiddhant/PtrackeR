import streamlit as st
import pandas as pd
import time
import random
from io import BytesIO
import os
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from yt_dlp import YoutubeDL
from fake_useragent import UserAgent
from typing import Optional

# Initialize UserAgent at the start
ua = UserAgent()

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

# Initialize session state
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'spotify_url_column' not in st.session_state:
    st.session_state.spotify_url_column = None
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = None
if 'spotify_df' not in st.session_state:
    st.session_state.spotify_df = None
if 'youtube_df' not in st.session_state:
    st.session_state.youtube_df = None

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
        if st.session_state.spotify_df is not None:
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
                    st.dataframe(updated_df)

    with col2:
        if st.session_state.youtube_df is not None:
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
                    st.dataframe(updated_df)
                    
                    if len(updated_df) > 0:
                        st.bar_chart(updated_df.set_index(youtube_url_column)['Views (Millions)'])

    # Export section
    st.markdown("### Export Options")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Export Spotify Data") and st.session_state.spotify_df is not None:
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
        if st.button("Export YouTube Data") and st.session_state.youtube_df is not None:
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
        if st.button("Export Combined Data") and all(df is not None for df in [st.session_state.spotify_df, st.session_state.youtube_df]):
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

# Usage Instructions
st.write("""
### Usage Instructions:
1. Upload an Excel file with separate sheets for Spotify and YouTube data
2. Select the appropriate sheets and click 'Load Data'
3. Select the URL columns for Spotify and YouTube
4. Process each dataset separately using the respective buttons
5. Export the processed data using the export options
""")

# Footer
st.markdown("---")
st.write("© ENIL. All rights reserved.")
