FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpoppler-cpp-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY app.py parsers.py analysis.py ai_comment.py ./
COPY templates templates/

# Expose port
EXPOSE 5000

# Run Flask app
CMD ["python", "-m", "flask", "run", "--host", "0.0.0.0"]
