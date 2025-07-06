#!/bin/bash

# Add library path for libzbar
export LD_LIBRARY_PATH=/usr/lib:/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH

# Run Gunicorn with Eventlet worker
exec gunicorn --worker-class eventlet --bind 0.0.0.0:5000 run:app
