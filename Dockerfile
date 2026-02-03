FROM python:3.12-slim

# Create non-root user
RUN useradd -m -r -s /bin/false streamer

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Switch to non-root user
USER streamer

# Run the application
CMD ["python", "-m", "src.main"]
