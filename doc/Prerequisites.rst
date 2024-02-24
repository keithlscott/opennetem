====================
Prerequisites
====================

----------
docker
----------
To run containers.

-------------------
Ability to be root
-------------------
Or possibly only the ability to run ``tc`` commands without a password.  This is required
in order to modify the ``tc netem`` qdiscs that implement link characteristics.

---------
Python3
---------
The emulator is a Python script.

------------------------------------------
docker compose (for the monitoring stack)
------------------------------------------

The monitoring stack uses docker compose, and the docker compose version for Ubuntu 22 is
quite old.  I followed the instructions below to install a newer version of docker and there
were others to get a recent version of docker compose.

https://www.digitalocean.com/community/tutorials/how-to-install-and-use-docker-on-ubuntu-22-04 


