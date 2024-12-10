#!/bin/bash
echo "\
[server]\n\
headless = true\n\
enableCORS=false\n\
port = $PORT\n\
" > ~/.streamlit/config.toml

# Install Playwright dependencies
playwright install chromium
