FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install only what's needed — no build tools for voice libs
COPY requirements-cloud.txt .
RUN pip install --no-cache-dir -r requirements-cloud.txt

# Copy the entire project
COPY . .

# Create the data directory (SQLite lives here)
RUN mkdir -p data

# Render injects PORT as an env var — default 8000 for local testing
ENV PORT=8000

# Start the FastAPI server
CMD uvicorn main:app --host 0.0.0.0 --port $PORT