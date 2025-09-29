#!/usr/bin/env python3
import docker
import re
from pprint import pprint
import argparse
import time
import json
import opennetem.utilities as utilities
import opennetem.runtime



def parse_sdrwatch_output(output: str) -> dict:
    """
    Parse the output of 'ion psmwatch' into a dictionary.
    """
    result = {
    }

    lines = [line.rstrip() for line in output.splitlines() if line.strip()]

    section = None
    for line in lines:
        if line.lower().startswith("small pool"):
            section = "small"
            continue
        elif line.lower().startswith("large pool"):
            section = "large"
            continue

        m = re.match(r"(\d+)\s+of size\s+(\d+)", line)
        if section == "small" and m:
            result["small_pool_free_blocks"].append(
                {"count": int(m.group(1)), "size": int(m.group(2))}
            )
            continue

        m = re.match(r"(\d+)\s+of order\s+(\d+)", line)
        if section == "large" and m:
            result["large_pool_free_blocks"].append(
                {"count": int(m.group(1)), "order": int(m.group(2))}
            )
            continue

        m = re.match(r"(.+?):\s+(\d+)", line)
        if m:
            key = f"{section}_"+m.group(1).strip().lower().replace(" ", "_")
            result[key] = int(m.group(2))

    return result


def run_sdrwatch_in_container(container_name: str) -> dict:
    """
    Run 'sdrwatch' in a container using Docker SDK and parse the output.
    """
    client = docker.from_env()
    container = client.containers.get(container_name)

    # Run command inside container
    exec_result = container.exec_run("sdrwatch ion")
    if exec_result.exit_code != 0:
        raise RuntimeError(
            f"sdrwatch failed with exit code {exec_result.exit_code}, stderr:\n{exec_result.output.decode()}"
        )

    output = exec_result.output.decode()
    return parse_sdrwatch_output(output)


def do_main():
    influxdb_support = utilities.influxdb_support()

    rtinfo = opennetem.runtime.opennetem_runtime()

    num_timeouts = 0
    interval = 5

    while num_timeouts<3:
        for container_name in rtinfo.list_nodes():
            parsed = run_sdrwatch_in_container(container_name)
            parsed["node_name"] = container_name

            if len(parsed.keys())==0:
                timeouts += 1
            else:
                timeouts = 0
                # print(json.dumps(parsed, indent=2))

                other_fields = parsed

                tags_dict = {"node_name": container_name}
                             
                influxdb_support.write_value("sdrwatch",
                                    f"sdrwatch info for node {container_name}",
                                    tags_dict = tags_dict,
                                    other_fields_dict=other_fields)

        time.sleep(interval)

        # pprint(parsed)


if __name__ == "__main__":
    do_main()

