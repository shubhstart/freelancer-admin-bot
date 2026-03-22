# Use Python 3.11 lightweight image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PORT 7860

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose the port (Hugging Face Spaces uses 7860 by default)
EXPOSE 7860

# Create application logs
RUN touch app.log && chmod 666 app.log

# Command to run with Gunicorn
# Using hardcoded 7860 to match Hugging Face default app_port
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "--timeout", "120", "--workers", "1", "--log-level", "debug", "--access-logfile", "-", "--error-logfile", "-", "run:app"]
