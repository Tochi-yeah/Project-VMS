#!/bin/bash
# run database migrations
flask db upgrade

# start the gunicorn server
exec gunicorn --worker-class eventlet -w 1 -b 0.0.0.0:5000 run:app
