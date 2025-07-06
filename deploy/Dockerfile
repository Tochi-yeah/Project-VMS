FROM python:3.13-slim

# Install system dependencies including zbar and runtime libraries
RUN apt-get update && \
    apt-get install -y libzbar0 libzbar-dev build-essential libglib2.0-0 && \
    ldconfig && \
    rm -rf /var/lib/apt/lists/*

# Set working directory (Render expects this)
WORKDIR /opt/render/project/src

# Copy application files
COPY . .

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expose application port
EXPOSE 5000

# Make start script executable
RUN chmod +x /opt/render/project/src/start.sh

# Set start command
CMD ["/opt/render/project/src/start.sh"]
