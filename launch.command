#!/usr/bin/env bash

# SmartClean macOS Launcher

cd "$(dirname "$0")"

echo "Checking environment..."
if ! command -v uv &> /dev/null; then
    echo "uv is not installed. Installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

echo "Setting up Python environment..."
uv venv
source .venv/bin/activate
uv pip install fastapi uvicorn websockets

echo "Building Frontend..."
cd frontend
npm run build
cd ..

echo "Starting Backend..."
cd backend
python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

echo "Backend started at PID $BACKEND_PID"

# Wait a moment for server to start
sleep 2

echo "Opening browser..."
open http://127.0.0.1:8000

# Wait for user to close the script
echo "Press Ctrl+C to exit and stop the server."
wait $BACKEND_PID
