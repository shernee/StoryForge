FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies directly (no venv needed in container)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Download Poppins fonts
RUN mkdir -p app/fonts && \
    BASE="https://github.com/google/fonts/raw/main/ofl/poppins" && \
    curl -sL "$BASE/Poppins-Regular.ttf" -o app/fonts/Poppins-Regular.ttf && \
    curl -sL "$BASE/Poppins-Bold.ttf"    -o app/fonts/Poppins-Bold.ttf && \
    curl -sL "$BASE/Poppins-Italic.ttf"  -o app/fonts/Poppins-Italic.ttf

# Copy application code
COPY app/ ./app/

# Create data directory
RUN mkdir -p data

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]