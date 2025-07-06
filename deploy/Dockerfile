FROM python:3.13-slim

# Install system dependencies including zbar and required libs
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libzbar0 libzbar-dev build-essential libglib2.0-0 && \
    ldconfig && \
    rm -rf /var/lib/apt/lists/*

# Set working directory (Render uses this path)
WORKDIR /opt/render/project/src

# Copy project files into container
COPY . .

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Make start.sh executable (if you’re using one — optional)
RUN chmod +x /opt/render/project/src/start.sh || true

# Expose the application port
EXPOSE 5000

# Set the default command to start your app
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "--bind", "0.0.0.0:5000", "run:app"]
