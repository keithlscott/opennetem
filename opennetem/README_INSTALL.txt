To install opennetem in an ACTIVE venv, type:

   pip3 install --editable .

That will install opennetem in the venv, and make links to the opennetem
'executables' listed in the pyproject.toml file such as:

    opennetem		(For running emulations)
    on_mon_rtt		Opennetem rtt monitoring script (runs on host)
    on_bpstats		Opennetem tool to monitor ION bpstats (runs on host)
    on_bplist		Opennetem tool to monitor ION queued bundles (runs on host)
