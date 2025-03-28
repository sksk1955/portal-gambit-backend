#!/bin/bash
set -e  # Exit on error

# Check if variable name argument is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 VARIABLE_NAME [OUTPUT_FILE]"
    echo "Example: $0 FIREBASE_CONFIG_STRING config/firebase_service_account.json"
    exit 1
fi

VAR_NAME=$1
OUTPUT_FILE=${2:-output.json}  # Default to output.json if not specified

# Debugging: Print environment variables
echo "Checking for environment variable: $VAR_NAME"
if [ -z "${!VAR_NAME}" ]; then
    echo "❌ Error: Variable $VAR_NAME not found!"
    env  # List all env variables for debugging
    exit 1
fi

# Decode base64 and write to file
echo -n "${!VAR_NAME}" | base64 --decode > "$OUTPUT_FILE"

# Validate JSON format (only if jq is available)
if command -v jq >/dev/null 2>&1; then
    if ! jq empty "$OUTPUT_FILE"; then
        echo "❌ Error: Decoded content is not valid JSON!"
        cat "$OUTPUT_FILE"  # Show the file contents for debugging
        exit 1
    fi
fi

echo "✅ Successfully decoded $VAR_NAME to $OUTPUT_FILE"
