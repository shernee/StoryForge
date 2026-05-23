#!/bin/bash

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip (try different approaches)
echo "Upgrading pip..."
python -m pip install --upgrade pip || python3 -m pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
python -m pip install -r requirements.txt || python3 -m pip install -r requirements.txt

# Download Poppins fonts
echo "Downloading Poppins fonts..."
mkdir -p app/fonts
BASE="https://github.com/google/fonts/raw/main/ofl/poppins"
curl -sL "$BASE/Poppins-Regular.ttf" -o app/fonts/Poppins-Regular.ttf
curl -sL "$BASE/Poppins-Bold.ttf"    -o app/fonts/Poppins-Bold.ttf
curl -sL "$BASE/Poppins-Italic.ttf"  -o app/fonts/Poppins-Italic.ttf

echo ""
echo "Setup complete! To activate the virtual environment and run the server:"
echo "source venv/bin/activate"
echo "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"