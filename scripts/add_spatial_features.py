"""
Add spatial features to ML dataset using network topology

This script adds:
1. Neighbor features (pressure, head, demand from neighbors)
2. Spatial gradients (difference between node and neighbors)
3. Topology-based features (degree, centrality)

Author: AI Assistant
Date: 2025-11-13
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List
import time


def load_topology(topology_file: str = "dataset/network_topology.csv") -> tuple:
    """
    Load network topology features
    
    Returns:
        (topology_df, neighbor_map)
    """
    print(f"📂 Loading topology from: {topology_file}")
    topology_df = pd.read_csv(topology_file)
    
    # Create neighbor mapping
    neighbor_map = {}
    for _, row in topology_df.iterrows():
        node_id = str(row['node_id'])
        neighbors_str = row['neighbors']
        
        if pd.notna(neighbors_str) and neighbors_str != '':
            neighbors = [n.strip() for n in neighbors_str.split(',')]
        else:
            neighbors = []
        
        neighbor_map[node_id] = neighbors
    
    print(f"✅ Topology loaded: {len(topology_df)} nodes")
    return topology_df, neighbor_map


def add_spatial_features_batch(
    df: pd.DataFrame,
    neighbor_map: Dict[str, List[str]],
    topology_df: pd.DataFrame,
    batch_size: int = 100000
) -> pd.DataFrame:
    """
    Add spatial features to dataframe in batches
    
    Args:
        df: DataFrame with columns: node_id, timestamp, pressure, head, demand, leak
        neighbor_map: {node_id: [neighbor_ids]}
        topology_df: DataFrame with topology features
        batch_size: Process in batches to avoid memory issues
    
    Returns:
        DataFrame with added spatial features
    """
    print(f"\n⏳ Adding spatial features to {len(df):,} records...")
    start_time = time.time()
    
    # Convert topology_df to dict for fast lookup
    topology_dict = topology_df.set_index('node_id').to_dict('index')
    
    # Initialize new columns
    df['neighbors_pressure_mean'] = 0.0
    df['neighbors_pressure_std'] = 0.0
    df['neighbors_head_mean'] = 0.0
    df['neighbors_demand_mean'] = 0.0
    df['pressure_gradient'] = 0.0
    df['head_gradient'] = 0.0
    df['node_degree'] = 0
    df['node_betweenness'] = 0.0
    df['node_elevation'] = 0.0
    
    # Process in batches
    n_batches = int(np.ceil(len(df) / batch_size))
    
    for batch_idx in range(n_batches):
        start_idx = batch_idx * batch_size
        end_idx = min((batch_idx + 1) * batch_size, len(df))
        
        if batch_idx % 10 == 0:
            elapsed = time.time() - start_time
            progress = (batch_idx / n_batches) * 100
            print(f"   Batch {batch_idx+1}/{n_batches} ({progress:.1f}%) - {elapsed:.1f}s elapsed")
        
        batch = df.iloc[start_idx:end_idx]
        
        # Group by timestamp for efficient neighbor lookup
        for timestamp, group in batch.groupby('timestamp'):
            # Create dict for fast lookup: {node_id: {pressure, head, demand}}
            node_data = {}
            for _, row in group.iterrows():
                node_id = str(row['node_id'])
                node_data[node_id] = {
                    'pressure': row['pressure'],
                    'head': row['head'],
                    'demand': row['demand']
                }
            
            # Compute neighbor features
            for idx, row in group.iterrows():
                node_id = str(row['node_id'])
                neighbors = neighbor_map.get(node_id, [])
                
                if neighbors:
                    # Get neighbor values
                    neighbor_pressures = [node_data[n]['pressure'] for n in neighbors if n in node_data]
                    neighbor_heads = [node_data[n]['head'] for n in neighbors if n in node_data]
                    neighbor_demands = [node_data[n]['demand'] for n in neighbors if n in node_data]
                    
                    if neighbor_pressures:
                        neighbors_pressure_mean = np.mean(neighbor_pressures)
                        neighbors_pressure_std = np.std(neighbor_pressures) if len(neighbor_pressures) > 1 else 0.0
                        pressure_gradient = row['pressure'] - neighbors_pressure_mean
                    else:
                        neighbors_pressure_mean = row['pressure']
                        neighbors_pressure_std = 0.0
                        pressure_gradient = 0.0
                    
                    if neighbor_heads:
                        neighbors_head_mean = np.mean(neighbor_heads)
                        head_gradient = row['head'] - neighbors_head_mean
                    else:
                        neighbors_head_mean = row['head']
                        head_gradient = 0.0
                    
                    if neighbor_demands:
                        neighbors_demand_mean = np.mean(neighbor_demands)
                    else:
                        neighbors_demand_mean = row['demand']
                else:
                    # No neighbors (reservoir/tank)
                    neighbors_pressure_mean = row['pressure']
                    neighbors_pressure_std = 0.0
                    neighbors_head_mean = row['head']
                    neighbors_demand_mean = row['demand']
                    pressure_gradient = 0.0
                    head_gradient = 0.0
                
                # Get topology features
                if node_id in topology_dict:
                    node_degree = topology_dict[node_id]['degree']
                    node_betweenness = topology_dict[node_id]['betweenness_centrality']
                    node_elevation = topology_dict[node_id]['elevation']
                else:
                    node_degree = 0
                    node_betweenness = 0.0
                    node_elevation = 0.0
                
                # Update dataframe
                df.at[idx, 'neighbors_pressure_mean'] = neighbors_pressure_mean
                df.at[idx, 'neighbors_pressure_std'] = neighbors_pressure_std
                df.at[idx, 'neighbors_head_mean'] = neighbors_head_mean
                df.at[idx, 'neighbors_demand_mean'] = neighbors_demand_mean
                df.at[idx, 'pressure_gradient'] = pressure_gradient
                df.at[idx, 'head_gradient'] = head_gradient
                df.at[idx, 'node_degree'] = node_degree
                df.at[idx, 'node_betweenness'] = node_betweenness
                df.at[idx, 'node_elevation'] = node_elevation
    
    elapsed = time.time() - start_time
    print(f"\n✅ Spatial features added in {elapsed:.1f}s ({elapsed/60:.1f} minutes)")
    print(f"   Added 9 new spatial features")
    
    return df


if __name__ == "__main__":
    print(f"\n{'='*80}")
    print("ADDING SPATIAL FEATURES TO ML DATASET")
    print(f"{'='*80}\n")
    
    # Paths
    topology_file = "dataset/network_topology.csv"
    input_file = "dataset/ml_data.parquet"  # Or your ML data file
    output_file = "dataset/ml_data_with_spatial.parquet"
    
    # Load topology
    topology_df, neighbor_map = load_topology(topology_file)
    
    # Load ML data (sample for testing)
    print(f"\n📂 Loading ML data from: {input_file}")
    df = pd.read_parquet(input_file)
    print(f"✅ ML data loaded: {len(df):,} records")
    
    # Add spatial features
    df = add_spatial_features_batch(df, neighbor_map, topology_df)
    
    # Save
    print(f"\n💾 Saving to: {output_file}")
    df.to_parquet(output_file, index=False, compression='snappy')
    print(f"✅ Saved!")
    
    # Print sample
    print(f"\n🔍 Sample with spatial features:")
    print(df[['node_id', 'timestamp', 'pressure', 'neighbors_pressure_mean', 
              'pressure_gradient', 'node_degree', 'leak']].head(10))
    
    print(f"\n{'='*80}")
    print("✅ SPATIAL FEATURES COMPLETE!")
    print(f"{'='*80}\n")












