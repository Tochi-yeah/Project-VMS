# Use an official lightweight Python base image
FROM python:3.13-slim

# Install system dependencies including zbar
RUN apt-get update && \
    apt-get install -y libzbar0 build-essential && \
    rm -rf /var/lib/apt/lists/*

# Set work directory inside the container
WORKDIR /app

# Copy project files into container
COPY . /app

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Run database migrations if needed
RUN flask db upgrade

# Expose port
EXPOSE 5000

# Start the app with gunicorn + eventlet
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "-b", "0.0.0.0:5000", "run:app"]
