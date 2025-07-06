#!/usr/bin/env bash

# Install required system packages
apt-get update
apt-get install -y libzbar0 libzbar-dev

# Install Python dependencies
pip install -r requirements.txt

ldconfig -p | grep zbar