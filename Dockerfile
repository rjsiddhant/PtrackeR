FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY packages.txt .
RUN apt-get update && xargs apt-get install -y < packages.txt \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and Firefox
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN playwright install --with-deps firefox

COPY . .
EXPOSE 8501

CMD ["streamlit", "run", "perp.py", "--server.port=8501", "--server.address=0.0.0.0"]
