#!/bin/bash
export LD_LIBRARY_PATH=/usr/lib:/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH
exec gunicorn --worker-class eventlet -b 0.0.0.0:5000 run:app
