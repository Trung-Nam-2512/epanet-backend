"""
Script test model leak detection với Top-K evaluation
"""
import pandas as pd
import numpy as np
import pickle
import json
from pathlib import Path

def load_model():
    """Load trained model"""
    model_file = Path("models/leak_detection_model.pkl")
    metadata_file = Path("models/model_metadata.json")
    
    if not model_file.exists():
        print("[ERROR] Model not found! Train first: python scripts/train_leak_model.py")
        return None, None
    
    with open(model_file, 'rb') as f:
        model = pickle.load(f)
    
    with open(metadata_file, 'r') as f:
        metadata = json.load(f)
    
    print("[OK] Model loaded successfully")
    print(f"  Features: {len(metadata['feature_cols'])} features")
    if 'optimal_threshold' in metadata:
        print(f"  Optimal threshold: {metadata['optimal_threshold']:.4f}")
    else:
        print(f"  Optimal threshold: 0.5 (default)")
    
    return model, metadata

def prepare_features(df):
    """Prepare features matching training pipeline"""
    print("[INFO] Preparing features...")
    
    # Time features (removed for bias prevention)
    df['hour'] = (df['timestamp'] / 3600).astype(int)
    
    # Enhanced features - process by scenario
    parts = []
    for scenario_id, sdf in df.groupby('scenario_id', sort=False):
        sdf = sdf.copy()
        g = sdf.groupby('node_id', sort=False)
        
        # Changes
        sdf['pressure_change'] = g['pressure'].diff().fillna(0)
        sdf['head_change'] = g['head'].diff().fillna(0)
        
        # Moving averages
        sdf['pressure_ma5'] = g['pressure'].rolling(5, min_periods=1).mean().reset_index(level=0, drop=True)
        sdf['head_ma5'] = g['head'].rolling(5, min_periods=1).mean().reset_index(level=0, drop=True)
        sdf['pressure_ma3'] = g['pressure'].rolling(3, min_periods=1).mean().reset_index(level=0, drop=True)
        sdf['head_ma3'] = g['head'].rolling(3, min_periods=1).mean().reset_index(level=0, drop=True)
        
        # Drops
        pressure_max = g['pressure'].rolling(5, min_periods=1).max().reset_index(level=0, drop=True)
        head_max = g['head'].rolling(5, min_periods=1).max().reset_index(level=0, drop=True)
        sdf['pressure_drop'] = pressure_max - sdf['pressure']
        sdf['head_drop'] = head_max - sdf['head']
        
        parts.append(sdf)
    
    df = pd.concat(parts, ignore_index=True)
    
    # Spatial features (network-level statistics)
    df['network_pressure_mean'] = df.groupby(['scenario_id', 'timestamp'])['pressure'].transform('mean')
    df['network_pressure_std'] = df.groupby(['scenario_id', 'timestamp'])['pressure'].transform('std')
    df['network_demand_mean'] = df.groupby(['scenario_id', 'timestamp'])['demand'].transform('mean')
    df['pressure_deviation'] = df['pressure'] - df['network_pressure_mean']
    df['demand_deviation'] = df.groupby('node_id')['demand'].transform(lambda x: x - x.mean())
    
    print("[OK] Features prepared")
    return df

def test_scenario(scenario_id, model, metadata, dataset_dir="dataset"):
    """Test model on a specific scenario"""
    print("\n" + "="*80)
    print(f"TESTING SCENARIO {scenario_id}")
    print("="*80)
    
    # Load scenario data
    scenario_dir = Path(dataset_dir) / f"scenario_{scenario_id:05d}"
    nodes_file = scenario_dir / "nodes.parquet"
    
    if not nodes_file.exists():
        print(f"[ERROR] Scenario file not found: {nodes_file}")
        return None
    
    df = pd.read_parquet(nodes_file)
    print(f"[OK] Loaded {len(df)} records")
    
    # Add scenario_id column
    df['scenario_id'] = scenario_id
    
    # Prepare features
    df = prepare_features(df)
    
    # Extract features
    feature_cols = metadata['feature_cols']
    X = df[feature_cols].values
    
    # Predict probabilities
    print("[INFO] Running prediction...")
    y_proba = model.predict_proba(X)[:, 1]
    df['leak_probability'] = y_proba
    
    # Apply optimal threshold
    threshold = metadata.get('optimal_threshold', 0.5)
    df['predicted_leak'] = (y_proba >= threshold).astype(int)
    
    # Get metadata for actual leaks
    metadata_file = Path(dataset_dir) / "metadata.csv"
    if metadata_file.exists():
        meta_df = pd.read_csv(metadata_file)
        scenario_meta = meta_df[meta_df['scenario_id'] == scenario_id].iloc[0]
        
        # Check if multiple leaks format
        if 'leak_nodes' in scenario_meta and pd.notna(scenario_meta['leak_nodes']):
            # Parse list format
            import ast
            leak_nodes = ast.literal_eval(scenario_meta['leak_nodes'])
            leak_starts = ast.literal_eval(scenario_meta['leak_start_times_s'])
            leak_ends = ast.literal_eval(scenario_meta['leak_end_times_s'])
            
            print(f"\n[INFO] Actual leaks in scenario:")
            for i, node in enumerate(leak_nodes):
                print(f"  - Node {node}: [{leak_starts[i]}s - {leak_ends[i]}s]")
        else:
            # Single leak format
            leak_node = str(scenario_meta['leak_node'])
            leak_start = scenario_meta['start_time_s']
            leak_end = scenario_meta['end_time_s']
            print(f"\n[INFO] Actual leak: Node {leak_node} [{leak_start}s - {leak_end}s]")
            leak_nodes = [leak_node]
            leak_starts = [leak_start]
            leak_ends = [leak_end]
    
    # Top-K Analysis (within leak time window)
    print(f"\n[INFO] Top-K Leak Localization:")
    
    for i, leak_node in enumerate(leak_nodes):
        t0, t1 = leak_starts[i], leak_ends[i]
        
        # Filter records in leak time window
        leak_window = df[(df['timestamp'] >= t0) & (df['timestamp'] <= t1)]
        
        if len(leak_window) == 0:
            print(f"  Leak #{i+1} ({leak_node}): No data in time window")
            continue
        
        # Aggregate probabilities per node (max probability in window)
        node_probs = leak_window.groupby('node_id')['leak_probability'].max().sort_values(ascending=False)
        
        # Get top-5 nodes
        top5_nodes = node_probs.head(5).index.tolist()
        top1_node = top5_nodes[0] if len(top5_nodes) > 0 else None
        
        # Check if actual leak node in top-K
        leak_node_str = str(leak_node)
        in_top1 = (str(top1_node) == leak_node_str)
        in_top5 = any(str(n) == leak_node_str for n in top5_nodes)
        
        print(f"\n  Leak #{i+1} - Node {leak_node}:")
        print(f"    Top-1: {top1_node} {'✓' if in_top1 else '✗'}")
        print(f"    Top-5: {top5_nodes[:5]}")
        print(f"    Result: {'✓ FOUND in Top-5' if in_top5 else '✗ NOT in Top-5'}")
        
        # Show probabilities
        print(f"\n    Top-10 Suspects:")
        for rank, (node, prob) in enumerate(node_probs.head(10).items(), 1):
            marker = " ← ACTUAL LEAK" if str(node) == leak_node_str else ""
            print(f"      {rank}. Node {node}: {prob:.4f}{marker}")
    
    return df

def test_multiple_scenarios(scenario_ids, model, metadata):
    """Test on multiple scenarios and compute aggregate metrics"""
    print("\n" + "="*80)
    print(f"TESTING ON {len(scenario_ids)} SCENARIOS")
    print("="*80)
    
    top1_correct = 0
    top5_correct = 0
    total_leaks = 0
    
    for scenario_id in scenario_ids:
        result = test_scenario(scenario_id, model, metadata)
        if result is not None:
            # Count this in aggregate (simplified - assumes single leak per scenario)
            # For full implementation, parse metadata and check each leak
            total_leaks += 1
    
    print("\n" + "="*80)
    print("AGGREGATE RESULTS")
    print("="*80)
    print(f"Scenarios tested: {len(scenario_ids)}")
    print(f"Note: For detailed Top-K accuracy, check individual scenario results above")

if __name__ == "__main__":
    import sys
    
    # Load model
    model, metadata = load_model()
    if model is None:
        sys.exit(1)
    
    # Test scenarios
    if len(sys.argv) > 1:
        # Test specific scenario(s)
        scenario_ids = [int(x) for x in sys.argv[1:]]
        for scenario_id in scenario_ids:
            test_scenario(scenario_id, model, metadata)
    else:
        # Test a few random scenarios from test set
        print("[INFO] No scenario specified, testing random samples from test set...")
        test_scenario_ids = [24, 30, 50, 52, 57]  # Same as in training output
        for scenario_id in test_scenario_ids:
            test_scenario(scenario_id, model, metadata)

