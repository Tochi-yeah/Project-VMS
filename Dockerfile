FROM python:3.13-slim

# Install system dependencies including zbar
RUN apt-get update && \
    apt-get install -y libzbar0 libzbar-dev build-essential libglib2.0-0 && \
    ldconfig && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

EXPOSE 5000

COPY start.sh /start.sh
RUN chmod +x /start.sh

CMD ["/start.sh"]
