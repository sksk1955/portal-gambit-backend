#!/bin/bash

# Check if variable name argument is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 VARIABLE_NAME [OUTPUT_FILE]"
    echo "Example: $0 MY_ENCODED_VAR output.json"
    exit 1
fi

# Get variable name and output file from arguments
VAR_NAME=$1
OUTPUT_FILE=${2:-output.json}  # Default to output.json if not specified

# Check if the environment variable exists
if [ -z "${!VAR_NAME}" ]; then
    echo "Error: Variable $VAR_NAME not found"
    exit 1
fi

# Decode base64 and write to file
echo "${!VAR_NAME}" | base64 --decode > "$OUTPUT_FILE"
cat "$OUTPUT_FILE"
# Check if decode was successful
if [ $? -eq 0 ]; then
    echo "Successfully decoded $VAR_NAME to $OUTPUT_FILE"
else
    echo "Error: Failed to decode base64 content"
    rm -f "$OUTPUT_FILE"  # Clean up failed output
    exit 1
fi