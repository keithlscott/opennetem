#!/usr/bin/bash


# Install Python virtual environment
pip install virtualenv
virtualenv venv
source venv/bin/activate
#pip3 install -r requirements.txt
#deactivate

# Install opennetem
pushd .
pip3 install --editable .
popd

#
# Link from 'user' opennetem executables installed by pyproject
# to /usr/local/bin so that they're in root's path to make it
# easier to run the emulator as root.
# 
echo "Linking opennetem executables to /usr/local/bin so that"
echo "they're in root's path (using sudo)."
EXECUTABLES="opennetem on_mon_rtt on_bplist on_bpstats"
for item in $EXECUTABLES; do
	sudo ln -s ~/.local/bin/${item} /usr/local/bin/$item
done

# Make opennetem html documentation
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

