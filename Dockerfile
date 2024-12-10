FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libxshmfence1 \
    libx11-xcb1 \
    libxcb-dri3-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and browsers
RUN pip install playwright==1.42.0
RUN playwright install --with-deps chromium

# Copy application code
COPY . .

# Expose port
EXPOSE 8501

# Command to run the application
CMD ["streamlit", "run", "perp.py", "--server.port=8501", "--server.address=0.0.0.0"]
