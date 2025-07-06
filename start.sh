#!/bin/bash

# Run database migrations (at runtime, with full env vars loaded)
flask db upgrade

# Start app with gunicorn + eventlet
gunicorn --worker-class eventlet -w 1 -b 0.0.0.0:5000 run:app
