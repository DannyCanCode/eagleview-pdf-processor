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

# Command to run the application
CMD python -c "import os; import subprocess; port = int(os.environ.get('PORT', '8000')); subprocess.run(['uvicorn', 'main:app', '--host', '0.0.0.0', '--port', str(port)])" 