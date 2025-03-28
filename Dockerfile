FROM python:3.11-slim

WORKDIR /app

RUN cat ~/.bashrc
# Copy requirements file first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .
ARG FIREBASE_CONFIG_STRING
ENV FIREBASE_CONFIG_STRING=${FIREBASE_CONFIG_STRING}
RUN chmod +x config/convert.sh
RUN config/convert.sh FIREBASE_CONFIG_STRING config/firebase_service_account.json

# Expose the port the app runs on
EXPOSE 8080

# Command to run the application
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}