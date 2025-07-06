# Use a lightweight official Python 3.13 image
FROM python:3.13-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install system dependencies (libzbar0 for pyzbar)
RUN apt-get update && \
    apt-get install -y libzbar0 && \
    rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy project files to the container
COPY . .

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Run database migrations
RUN flask db upgrade

# Expose the port your app runs on
EXPOSE 10000

# Command to run the app
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "run:app"]
