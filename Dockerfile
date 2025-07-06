FROM python:3.13-slim

# Install system dependencies including zbar
RUN apt-get update && \
    apt-get install -y libzbar0 libzbar-dev build-essential && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expose port
EXPOSE 5000

# Copy and give execution permission to start.sh
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Start with start.sh
CMD ["/start.sh"]
