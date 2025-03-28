#!/bin/bash

# Exit on any error
set -e

# Convert Firebase config
config/convert.sh FIREBASE_CONFIG config/firebase_service_account.json

# Start the application using uvicorn
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8080}"