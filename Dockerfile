FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the port (this is just documentation)
EXPOSE 8000

# Command to run the application using Railway's PORT environment variable
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} 