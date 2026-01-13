#!/bin/bash

echo "🚀 Launching Antigravity IDE with Remote Debugging enabled..."
echo "Port: 9000"

# Adjust the path if your Antigravity.app is located elsewhere
APP_PATH="/Applications/Antigravity.app"

if [ ! -d "$APP_PATH" ]; then
    echo "Error: Antigravity.app not found at $APP_PATH"
    echo "Please update the script with the correct path."
    exit 1
fi

open -a "$APP_PATH" --args --remote-debugging-port=9000

echo "✅ App launched. Please wait for it to initialize before running the driver."
