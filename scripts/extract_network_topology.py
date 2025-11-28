"""
Extract network topology features from EPANET .inp file

This script extracts:
1. Pipe connectivity (network graph)
2. Node neighbors
3. Spatial features (centrality, degree)
4. Node elevation
5. Pipe characteristics (diameter, length)

Author: AI Assistant
Date: 2025-11-13
"""

import wntr
import networkx as nx
import pandas as pd
import numpy as np
from pathlib import Path


def extract_topology_features(inp_file: str, output_file: str = "dataset/network_topology.csv"):
    """
    Extract network topology features from EPANET .inp file
    
    Args:
        inp_file: Path to .inp file
        output_file: Path to save topology features CSV
    
    Returns:
        pd.DataFrame with columns:
            - node_id: Node ID (string)
            - elevation: Node elevation (m)
            - degree: Number of connected pipes
            - neighbors: List of neighbor node IDs
            - betweenness_centrality: Betweenness centrality
            - closeness_centrality: Closeness centrality
            - clustering_coefficient: Clustering coefficient
            - is_junction: Boolean (True if junction, False if reservoir/tank)
    """
    print(f"\n{'='*80}")
    print("EXTRACTING NETWORK TOPOLOGY FEATURES")
    print(f"{'='*80}\n")
    
    # Load EPANET network
    print(f"📂 Loading network from: {inp_file}")
    wn = wntr.network.WaterNetworkModel(inp_file)
    
    # Get network graph
    G = wn.to_graph()
    print(f"✅ Network loaded: {len(wn.node_name_list)} nodes, {len(wn.link_name_list)} links")
    
    # Extract features for each node
    topology_features = []
    
    print(f"\n⏳ Extracting topology features...")
    
    # Convert to simple graph if MultiGraph (for clustering coefficient)
    # Water networks can have multiple pipes between same nodes
    if isinstance(G, (nx.MultiGraph, nx.MultiDiGraph)):
        print("   Converting MultiGraph to Graph for analysis...")
        G_simple = nx.Graph(G)  # Convert to simple graph (removes multi-edges)
    else:
        G_simple = G
    
    # Compute centrality metrics (only once for all nodes)
    print("   Computing betweenness centrality...")
    betweenness = nx.betweenness_centrality(G_simple)
    
    print("   Computing closeness centrality...")
    closeness = nx.closeness_centrality(G_simple)
    
    print("   Computing clustering coefficient...")
    clustering = nx.clustering(G_simple)
    
    # Extract features for each node
    for node_name in wn.node_name_list:
        node = wn.get_node(node_name)
        
        # Get neighbors (use simple graph to avoid duplicates)
        neighbors = list(G_simple.neighbors(node_name))
        
        # Node features
        feature = {
            'node_id': str(node_name),
            'node_type': node.node_type,
            'elevation': node.elevation if hasattr(node, 'elevation') else 0.0,
            'degree': G_simple.degree(node_name),  # Use simple graph
            'num_neighbors': len(neighbors),
            'neighbors': ','.join(str(n) for n in neighbors),
            'betweenness_centrality': betweenness[node_name],
            'closeness_centrality': closeness[node_name],
            'clustering_coefficient': clustering[node_name],
            'is_junction': node.node_type == 'Junction'
        }
        
        topology_features.append(feature)
    
    # Create DataFrame
    df = pd.DataFrame(topology_features)
    
    # Sort by node_id
    df = df.sort_values('node_id').reset_index(drop=True)
    
    # Save to CSV
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    
    print(f"\n✅ Topology features extracted!")
    print(f"   Total nodes: {len(df)}")
    print(f"   Junctions: {df['is_junction'].sum()}")
    print(f"   Reservoirs/Tanks: {(~df['is_junction']).sum()}")
    print(f"   Saved to: {output_path}")
    
    # Print statistics
    print(f"\n📊 Topology Statistics:")
    print(f"   Degree - Min: {df['degree'].min()}, Max: {df['degree'].max()}, Mean: {df['degree'].mean():.2f}")
    print(f"   Betweenness - Min: {df['betweenness_centrality'].min():.4f}, Max: {df['betweenness_centrality'].max():.4f}")
    print(f"   Elevation - Min: {df['elevation'].min():.2f}, Max: {df['elevation'].max():.2f}")
    
    return df


def create_neighbor_mapping(topology_df: pd.DataFrame) -> dict:
    """
    Create a mapping from node_id to list of neighbor node_ids
    
    Args:
        topology_df: DataFrame with 'node_id' and 'neighbors' columns
    
    Returns:
        dict: {node_id: [neighbor1, neighbor2, ...]}
    """
    neighbor_map = {}
    
    for _, row in topology_df.iterrows():
        node_id = str(row['node_id'])
        neighbors_str = row['neighbors']
        
        if pd.notna(neighbors_str) and neighbors_str != '':
            neighbors = [n.strip() for n in neighbors_str.split(',')]
        else:
            neighbors = []
        
        neighbor_map[node_id] = neighbors
    
    return neighbor_map


if __name__ == "__main__":
    import sys
    
    # Default paths
    inp_file = "epanetVip1.inp"
    output_file = "dataset/network_topology.csv"
    
    # Allow command line args
    if len(sys.argv) > 1:
        inp_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    
    # Extract features
    df = extract_topology_features(inp_file, output_file)
    
    # Test neighbor mapping
    neighbor_map = create_neighbor_mapping(df)
    print(f"\n🔍 Sample neighbor mapping:")
    sample_nodes = list(neighbor_map.keys())[:5]
    for node in sample_nodes:
        print(f"   Node {node}: {len(neighbor_map[node])} neighbors → {neighbor_map[node][:3]}...")
    
    print(f"\n{'='*80}")
    print("✅ TOPOLOGY EXTRACTION COMPLETE!")
    print(f"{'='*80}\n")

