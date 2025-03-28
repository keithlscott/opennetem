#
# Network stuff
#

# The topology DF looks like this:
#
# 2025-03-05 09:53:07,842 - opennetem.topology - DEBUG - After converting to lower self.df is:
#      time  source    dest   delay      rate
# 0     0.0  node_a  node_b      0s   100kbit
# 1     NaN  node_b  node_a      0s   150kbit
# 2    30.0  node_a  node_b      3s   100kbit
# 3     NaN  node_b  node_a      4s   150kbit
# 4     NaN     NaN  node_c      2s    50kbit
# 5     NaN  node_c  node_b      1s   100kbit
# 6    60.0  node_a  node_b     NaN       NaN
# 7     NaN  node_b  node_a     NaN       NaN
# 8     NaN  node_b  node_c     NaN       NaN
# 9     NaN  node_c  node_b     NaN       NaN
# 10   90.0  node_a  node_b   500ms   100kbit
# 11    NaN  node_b  node_c  1400ms   200kbit

import sys
import os
import shutil
import pandas
import networkx as nx
import matplotlib.pyplot as plt
import logging
import opennetem.topology as topology
import opennetem.my_logging as my_logging
import base64
import json

logger = logging.getLogger("opennetem.network")

class MultiTopologyError(Exception):
    def __init__(self, msg="df_to_network called with multiple configs, expected a unique time element"):
        super().__init__(self.msg)

    def __str__(self):
        return f'{self.msg}'


def df_to_network(df: pandas.DataFrame) -> nx.DiGraph:
    """Convert a dataframe representing a network topology configuration to a networkX network."""

    the_times = df['time'].unique()
    if len(list(the_times)) > 1:
        raise MultiTopologyError()
    
    all_unique = []
    sources = df["source"].unique()
    dests = df["dest"].unique()
    all_unique = sources.copy()

    for d in dests:
        if d not in all_unique:
            all_unique += [d]
    
    G = nx.DiGraph()
    for index, row in df.iterrows():
        G.add_node(row["source"])
        G.add_node(row["dest"])
        if pandas.isna(row["rate"]):
            pass
        else:
            G.add_edge(row["source"], row["dest"])

    # print(G)
    # print(G.nodes)
    # print(G.edges)

    return(G)


def df_to_network_list(df: pandas.DataFrame) -> nx.DiGraph:
    """Convert a dataframe representing multiple network topologies into a list of networkX DiGraphs"""

    logger.info(f"Column names: {list(df)}")
    the_times = df['time'].unique()

    pos = None
    graphs = []
    for t in the_times:
        tmp_df = df.loc[df["time"] == t]
        G = df_to_network(tmp_df)
        G.opennetem_time = int(t)
        graphs += [G]
    return(graphs)


def make_topology_figures(topology_df: pandas.DataFrame, dir_name:str ="./topology_images") ->list[plt.figure]:
    """Generate png files representing the network topology at each timestep of the topology_df.

    Files are written to .topology_images and returned as a list.

    Args:
        topology_df (pandas.DataFrame): Dataframe of network topologies.
        dir_name (str): directory into which to write the png files
    """
    the_times = topology_df['time'].unique()

    pos = None
    graphs = df_to_network_list(topology_df)
    
    # Used later to ensure consistent plot positions; needed even when
    # positions are given to ensure bounding box is right
    all_possible = nx.DiGraph()
    for index, row in topology_df.iterrows():
            all_possible.add_edge(row["source"], row["dest"])

    #
    # Figure out node positions
    # Use a user-provided file if there is one, otherwise generate from a fully-
    # connected network.
    #
    if os.path.exists("./node_positions.txt"):
        logger.info("Using node positions from file.")
        with open("./node_positions.txt") as fp:
                data = fp.read().strip().rstrip()
        pos = eval(data)           # This is a massive security hole

    else:
        pos = nx.spring_layout(all_possible)

        logger.info("FIXME: set graph positions in scenario file not separate text file.")
        with open("/var/run/opennetem/node_positions.txt", "w") as fp:
                fp.write(str({x, list(pos[x])} for x in pos))
    
    #
    # Make topology_images directory and remove everything from it.
    #
    os.makedirs(dir_name, exist_ok=True)

    for filename in os.listdir(dir_name):
        file_path = os.path.join(dir_name, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
                print('Failed to delete %s. Reason: %s' % (file_path, e))

    all_figs = []
    for g in graphs:
        fig = plt.figure(figsize=(12,12))
        fig.suptitle(f"Topology at time {g.opennetem_time}", fontsize=16)

        ax = plt.subplot(111)
        ax.set_title('Graph - Shapes', fontsize=10)

        for n in all_possible.nodes:
            if n not in g.nodes:
                g.add_node(n)

        # pos = nx.spring_layout(G)
        nx.draw(g, pos, node_size=1500, with_labels=True, node_color='yellow', font_size=8, font_weight='bold')

        plt.tight_layout()
        plt.savefig(f"{dir_name}/time_{g.opennetem_time}.png", format="PNG")
        all_figs += [fig]
    
    return(all_figs)


def base64_figures(dir_name):
    "base64 encode the topology figure PNG files and return a list of [[time, encoded_image], ...]"

    results = []
    for filename in os.listdir(dir_name):
        file_path = os.path.join(dir_name, filename)
        try:
            with open(file_path, "rb") as fp:
                data = fp.read()
                data64_bytes = base64.b64encode(data)
                base64_str = data64_bytes.decode("utf-8")
                toks = filename.split("_")[1]
                toks = toks.split(".")
                results += [[float(toks[0]), base64_str]]

        except Exception as e:
                print('Failed to base64 encode %s. Reason: %s' % (file_path, e))

    results = sorted(results, key=lambda x: x[0])

    return(results)


