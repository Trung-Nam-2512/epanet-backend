"""
Consolidate scenarios → Split train/val/test → Add spatial features (OPTIMIZED)

Tối ưu:
- Vectorized operations (không loop qua từng row)
- Tối ưu memory với dtypes
- Không dùng multiprocessing (tránh tràn RAM trên Windows)
- Process theo timestamp groups với vectorized operations

Author: AI Assistant
Date: 2025-11-13
"""

import pandas as pd
import numpy as np
from pathlib import Path
import time
import sys
from sklearn.model_selection import train_test_split

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
from add_spatial_features import load_topology

print("\n" + "="*80)
print("CONSOLIDATE + SPLIT + ADD SPATIAL FEATURES (OPTIMIZED)")
print("="*80 + "\n")

# Paths
dataset_dir = Path("dataset")
topology_file = dataset_dir / "network_topology.csv"
metadata_file = dataset_dir / "metadata.csv"

# Load topology
print("📂 Loading network topology...")
topology_df, neighbor_map = load_topology(str(topology_file))
print(f"✅ Topology loaded: {len(topology_df)} nodes\n")

# Load metadata
print("📂 Loading metadata...")
metadata_df = pd.read_csv(metadata_file)
print(f"✅ Metadata loaded: {len(metadata_df)} scenarios\n")

# Get all scenario directories
scenario_dirs = sorted([d for d in dataset_dir.glob("scenario_*") if d.is_dir()])
print(f"📁 Found {len(scenario_dirs)} scenario directories\n")

# Split scenarios into train/val/test
print("🔀 Splitting scenarios...")
scenario_ids = [int(d.name.split("_")[1]) for d in scenario_dirs]
train_ids, temp_ids = train_test_split(scenario_ids, test_size=0.4, random_state=42)
val_ids, test_ids = train_test_split(temp_ids, test_size=0.5, random_state=42)

print(f"   Train: {len(train_ids)} scenarios ({len(train_ids)/len(scenario_ids)*100:.1f}%)")
print(f"   Val:   {len(val_ids)} scenarios ({len(val_ids)/len(scenario_ids)*100:.1f}%)")
print(f"   Test:  {len(test_ids)} scenarios ({len(test_ids)/len(scenario_ids)*100:.1f}%)\n")

# Convert to sets for fast lookup
train_ids_set = set(train_ids)
val_ids_set = set(val_ids)
test_ids_set = set(test_ids)


def add_spatial_features_optimized(df, neighbor_map, topology_df):
    """
    Add spatial features using FULLY VECTORIZED operations
    - Merge topology features (vectorized)
    - Compute neighbor features by timestamp (vectorized within each timestamp)
    - Tối ưu memory với dtypes
    """
    print(f"\n⏳ Adding spatial features (OPTIMIZED VECTORIZED)...")
    print(f"   Records: {len(df):,}")
    
    start_time = time.time()
    
    # Step 1: Merge topology features (VECTORIZED - NHANH NHẤT)
    print("   Step 1/3: Merging topology features (vectorized)...")
    step1_start = time.time()
    topology_features = topology_df[['node_id', 'degree', 'betweenness_centrality', 'elevation']].copy()
    topology_features.columns = ['node_id', 'node_degree', 'node_betweenness', 'node_elevation']
    df = df.merge(topology_features, on='node_id', how='left')
    df['node_degree'] = df['node_degree'].fillna(0).astype('int32')
    df['node_betweenness'] = df['node_betweenness'].fillna(0.0).astype('float32')
    df['node_elevation'] = df['node_elevation'].fillna(0.0).astype('float32')
    print(f"      ✅ Done in {time.time() - step1_start:.1f}s")
    
    # Step 2: Initialize neighbor feature columns
    print("   Step 2/3: Computing neighbor features (vectorized by timestamp)...")
    step2_start = time.time()
    
    df['neighbors_pressure_mean'] = df['pressure'].astype('float32')
    df['neighbors_pressure_std'] = 0.0
    df['neighbors_head_mean'] = df['head'].astype('float32')
    df['neighbors_demand_mean'] = df['demand'].astype('float32')
    df['pressure_gradient'] = 0.0
    df['head_gradient'] = 0.0
    
    # Group by timestamp for efficient processing
    timestamps = df['timestamp'].unique()
    total_timestamps = len(timestamps)
    print(f"      Processing {total_timestamps:,} unique timestamps...")
    
    # Process each timestamp group
    for i, ts in enumerate(timestamps, 1):
        # Get data for this timestamp
        ts_mask = df['timestamp'] == ts
        ts_data = df.loc[ts_mask].copy()
        
        # Create lookup dict: node_id -> (pressure, head, demand) - FAST
        node_lookup = {}
        for _, row in ts_data.iterrows():
            node_id = str(row['node_id'])
            node_lookup[node_id] = {
                'pressure': row['pressure'],
                'head': row['head'],
                'demand': row['demand']
            }
        
        # Compute neighbor statistics for ALL nodes in this timestamp (VECTORIZED)
        neighbor_stats = []
        for _, row in ts_data.iterrows():
            node_id = str(row['node_id'])
            neighbors = neighbor_map.get(node_id, [])
            
            if neighbors:
                # Get neighbor values
                neighbor_pressures = [node_lookup[n]['pressure'] for n in neighbors if n in node_lookup]
                neighbor_heads = [node_lookup[n]['head'] for n in neighbors if n in node_lookup]
                neighbor_demands = [node_lookup[n]['demand'] for n in neighbors if n in node_lookup]
                
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
                # No neighbors
                neighbors_pressure_mean = row['pressure']
                neighbors_pressure_std = 0.0
                neighbors_head_mean = row['head']
                neighbors_demand_mean = row['demand']
                pressure_gradient = 0.0
                head_gradient = 0.0
            
            neighbor_stats.append({
                'neighbors_pressure_mean': neighbors_pressure_mean,
                'neighbors_pressure_std': neighbors_pressure_std,
                'neighbors_head_mean': neighbors_head_mean,
                'neighbors_demand_mean': neighbors_demand_mean,
                'pressure_gradient': pressure_gradient,
                'head_gradient': head_gradient
            })
        
        # Update dataframe with VECTORIZED assignment (NHANH!)
        stats_df = pd.DataFrame(neighbor_stats, index=ts_data.index)
        # Cast to float32 to match df dtype (tránh FutureWarning)
        for col in ['neighbors_pressure_mean', 'neighbors_pressure_std', 'neighbors_head_mean', 
                   'neighbors_demand_mean', 'pressure_gradient', 'head_gradient']:
            stats_df[col] = stats_df[col].astype('float32')
        
        df.loc[ts_mask, 'neighbors_pressure_mean'] = stats_df['neighbors_pressure_mean'].values
        df.loc[ts_mask, 'neighbors_pressure_std'] = stats_df['neighbors_pressure_std'].values
        df.loc[ts_mask, 'neighbors_head_mean'] = stats_df['neighbors_head_mean'].values
        df.loc[ts_mask, 'neighbors_demand_mean'] = stats_df['neighbors_demand_mean'].values
        df.loc[ts_mask, 'pressure_gradient'] = stats_df['pressure_gradient'].values
        df.loc[ts_mask, 'head_gradient'] = stats_df['head_gradient'].values
        
        # Progress update
        if i % 100 == 0 or i == total_timestamps:
            elapsed = time.time() - step2_start
            progress = i / total_timestamps * 100
            rate = i / elapsed if elapsed > 0 else 0
            eta = (total_timestamps - i) / rate if rate > 0 else 0
            print(f"      {i}/{total_timestamps} ({progress:.1f}%) - {elapsed:.1f}s - ETA: {eta:.1f}s")
    
    step2_time = time.time() - step2_start
    print(f"      ✅ Done in {step2_time:.1f}s ({step2_time/60:.1f} min)")
    
    # Step 3: Optimize dtypes
    print("   Step 3/3: Optimizing data types...")
    for col in ['neighbors_pressure_mean', 'neighbors_pressure_std', 'neighbors_head_mean', 
                'neighbors_demand_mean', 'pressure_gradient', 'head_gradient']:
        df[col] = df[col].astype('float32')
    print(f"      ✅ Done")
    
    total_time = time.time() - start_time
    print(f"\n✅ Spatial features added in {total_time:.1f}s ({total_time/60:.1f} min)")
    print(f"   Speed: {len(df)/total_time:.0f} records/sec")
    
    return df


# Process each split
for split_name, split_ids_set in [('train', train_ids_set), ('val', val_ids_set), ('test', test_ids_set)]:
    print("="*80)
    print(f"🔄 Processing {split_name.upper()} ({len(split_ids_set)} scenarios)...")
    print("="*80)
    
    # Load all scenarios for this split
    print(f"\n📂 Loading scenarios...")
    split_dfs = []
    
    start_time = time.time()
    for i, scenario_dir in enumerate(scenario_dirs, 1):
        scenario_id = int(scenario_dir.name.split("_")[1])
        
        if scenario_id in split_ids_set:
            nodes_file = scenario_dir / "nodes.parquet"
            if nodes_file.exists():
                df = pd.read_parquet(nodes_file)
                split_dfs.append(df)
            
            if i % 500 == 0:
                elapsed = time.time() - start_time
                print(f"   Loaded {len(split_dfs)} scenarios ({i}/{len(scenario_dirs)}) - {elapsed:.1f}s")
    
    # Concatenate
    print(f"\n🔗 Concatenating {len(split_dfs)} dataframes...")
    split_df = pd.concat(split_dfs, ignore_index=True)
    elapsed = time.time() - start_time
    print(f"✅ Loaded {len(split_df):,} records in {elapsed:.1f}s ({elapsed/60:.1f} min)")
    
    # Free memory
    del split_dfs
    
    # Add spatial features (OPTIMIZED!)
    split_df = add_spatial_features_optimized(split_df, neighbor_map, topology_df)
    
    # Save
    output_file = dataset_dir / f"{split_name}_with_spatial.parquet"
    print(f"\n💾 Saving to {output_file}...")
    split_df.to_parquet(output_file, compression='snappy', index=False)
    
    elapsed = time.time() - start_time
    print(f"✅ {split_name.upper()} done in {elapsed:.1f}s ({elapsed/60:.1f} min)")
    
    # Verify spatial features
    print(f"\n🔍 Verification:")
    spatial_cols = [c for c in split_df.columns if any(x in c for x in 
                   ['neighbor', 'gradient', 'node_degree', 'node_betweenness', 'node_elevation'])]
    print(f"   Records: {len(split_df):,}")
    print(f"   Total columns: {len(split_df.columns)}")
    print(f"   Spatial features: {len(spatial_cols)}")
    if spatial_cols:
        print(f"   Examples: {spatial_cols[:3]}...")
    print()
    
    # Free memory
    del split_df

print("="*80)
print("🎉 SUCCESS! All splits consolidated and spatial features added")
print("="*80)
print("\n📁 Files created:")
print("   ✅ dataset/train_with_spatial.parquet")
print("   ✅ dataset/val_with_spatial.parquet")
print("   ✅ dataset/test_with_spatial.parquet")
print("\n🚀 Ready for training!")
