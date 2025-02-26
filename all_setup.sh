#!/usr/bin/bash


# Install Python virtual environment
apt install python3-virtualenv
virtualenv venv
source venv/bin/activate
pip3 install -r requirements.txt
deactivate

# Make documentation
cd doc
make html
cd ..

# Build the docker images used by opennetem
cd netem_images
./build_images.sh
cd ..

# Restore the data volumes used by the monitoring stack
# This includes things like the database configuration
# and Grafana dashboard configurations
cd monitor
./restore_volumes.sh
cd ..

# Start the monitoring stack
# This can be left running.  If you do stop it
# (with docker-compose down in the monitor directory)
# you'll need to restart it if you want monitoring
# capabilities.
cd monitor
docker-compose up -d
cd ..

