FROM python:3.13-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y libzbar0 build-essential && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

EXPOSE 5000

# Copy and give execution permission
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Use start.sh as the container's start command
CMD ["/start.sh"]