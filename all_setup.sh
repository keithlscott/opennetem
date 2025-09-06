#!/usr/bin/bash

apt -y update

################################################
#
# Install python3
#
apt -y install python3 python3-pip


################################################
#
# Install docker-ce
#

# Install a few prerequisite packages which let apt use packages over HTTPS:
apt -y install apt-transport-https ca-certificates curl software-properties-common

# Add the GPG key for the official Docker repository to your system:
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc

# Add the Docker repository to APT sources
echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
    $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
    tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update existing list of packages again for the addition to be recognized:
apt -y update

# Make sure you are about to install from the Docker repo instead of the default Ubuntu repo:
apt-cache policy docker-ce

# Install docker
apt -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin


################################################
#
# Install Python virtual environment
#
apt -y install python3-virtualenv

virtualenv venv
source venv/bin/activate


################################################
#
# 'Install' opennetem and apps.
# The pyproject file will direct install to make some 'executables' under
# ~/.local/bin which we'll then link to /usr/local/bin so they're easy to
# find when we run the emulator as root.
#
pushd .
cd opennetem/
pip3 install --editable .
popd

# Link from 'user' opennetem executables installed by pyproject
# to /usr/local/bin so that they're in root's path to make it
# easier to run the emulator as root.
#
# These 'executables' are installed via the 'pip3 install --editable .'
# command above
#
echo "Linking opennetem executables to /usr/local/bin so that"
echo "they're in root's path (e.g. when using sudo)."
EXECUTABLES="opennetem on_mon_rtt on_bplist on_bpstats on_setup_ion_dbinfo"
for item in $EXECUTABLES; do
	ln -s ~/.local/bin/${item} /usr/local/bin/$item
done


################################################
#
# Make opennetem html documentation
#
pushd .
pip3 install Sphinx
cd doc
make html
popd


################################################
#
# Build the docker images used by opennetem
#
pushd .
cd netem_images
./build_images.sh
popd


################################################
#
# Restore the data volumes used by the monitoring stack
# This includes things like the database configuration
# and Grafana dashboard configurations
#
pushd .
cd monitor
./restore_volumes.sh
popd


################################################
#
# Start the monitoring stack
# This can be left running.  If you do stop it
# (with docker-compose down in the monitor directory)
# you'll need to restart it if you want monitoring
# capabilities.
#
pushd .
cd monitor
docker compose up -d
popd


################################################
#
# Make everything here owned by the user:group (not root)
#
chown -R $(echo $SUDO_USER):$(id -gn $SUDO_USER) ${1} -h .

