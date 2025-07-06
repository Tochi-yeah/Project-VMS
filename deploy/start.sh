#!/bin/bash

# Ensure libzbar is in the library path
export LD_LIBRARY_PATH=/usr/lib:/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH

# Start Gunicorn with eventlet worker
exec gunicorn --worker-class eventlet -w 1 -b 0.0.0.0:5000 run:app
