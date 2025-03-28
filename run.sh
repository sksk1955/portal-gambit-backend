#!/bin/bash

# Exit on any error
set -e

echo "$FIREBASE_CONFIG_STRING"
echo "$JWT_SECRET"
echo "$FIREBASE_DATABASE_URL"


# Convert Firebase config
config/convert.sh FIREBASE_CONFIG_STRING config/firebase_service_account.json

# Start the application using uvicorn
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8080}"