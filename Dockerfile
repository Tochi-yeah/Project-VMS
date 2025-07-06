FROM python:3.13-slim

# Install zbar shared library
RUN apt-get update && \
    apt-get install -y libzbar0 && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy all files into container
COPY . /app

# Install dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# Set LD_LIBRARY_PATH so pyzbar can find libzbar
ENV LD_LIBRARY_PATH=/usr/lib

# Expose port
EXPOSE 5000

# Copy and set permission for start.sh
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Run start script
CMD ["/start.sh"]
