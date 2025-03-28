FROM python:3.11-slim

WORKDIR /app

# Install necessary tools
RUN apt-get update && apt-get install -y bash && rm -rf /var/lib/apt/lists/*

# Copy requirements file first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Ensure script is executable
RUN chmod +x config/convert.sh

# Expose the port the app runs on
EXPOSE 8080

# Command to run the application
CMD bash -c "config/convert.sh \"$FIREBASE_CONFIG_STRING\" config/firebase_service_account.json && exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"
