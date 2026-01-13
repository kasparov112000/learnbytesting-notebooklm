FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright for browser auth (needed for notebooklm-py)
RUN playwright install chromium --with-deps || echo "Playwright install skipped"

# Copy application code
COPY src/ ./src/

# Expose port
EXPOSE 3034

# Run the application
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "3034"]
