"""
🎯 DEMO: Leak Detection System
Presentation-ready demo script with beautiful output
"""
import pandas as pd
import numpy as np
import pickle
import json
from pathlib import Path
import sys

def print_header(title):
    """Print beautiful header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")

def print_section(title):
    """Print section title"""
    print(f"\n{'─'*80}")
    print(f"  {title}")
    print(f"{'─'*80}")

def load_model():
    """Load trained model"""
    print_section("📦 LOADING MODEL")
    
    model_file = Path("models/leak_detection_model.pkl")
    metadata_file = Path("models/model_metadata.json")
    
    if not model_file.exists():
        print("❌ Model not found! Please train first: python scripts/train_leak_model.py")
        return None, None
    
    with open(model_file, 'rb') as f:
        model = pickle.load(f)
    
    with open(metadata_file, 'r') as f:
        metadata = json.load(f)
    
    print(f"✅ Model loaded successfully")
    print(f"   • Features: {len(metadata['feature_cols'])}")
    print(f"   • Training Date: {metadata.get('timestamp', 'N/A')}")
    
    return model, metadata

def prepare_features(df, scenario_id):
    """Prepare features for prediction"""
    df['scenario_id'] = scenario_id
    df['hour'] = (df['timestamp'] / 3600).astype(int)
    
    # Enhanced features
    parts = []
    for sid, sdf in df.groupby('scenario_id', sort=False):
        sdf = sdf.copy()
        g = sdf.groupby('node_id', sort=False)
        
        sdf['pressure_change'] = g['pressure'].diff().fillna(0)
        sdf['head_change'] = g['head'].diff().fillna(0)
        
        sdf['pressure_ma5'] = g['pressure'].rolling(5, min_periods=1).mean().reset_index(level=0, drop=True)
        sdf['head_ma5'] = g['head'].rolling(5, min_periods=1).mean().reset_index(level=0, drop=True)
        sdf['pressure_ma3'] = g['pressure'].rolling(3, min_periods=1).mean().reset_index(level=0, drop=True)
        sdf['head_ma3'] = g['head'].rolling(3, min_periods=1).mean().reset_index(level=0, drop=True)
        
        pressure_max = g['pressure'].rolling(5, min_periods=1).max().reset_index(level=0, drop=True)
        head_max = g['head'].rolling(5, min_periods=1).max().reset_index(level=0, drop=True)
        sdf['pressure_drop'] = pressure_max - sdf['pressure']
        sdf['head_drop'] = head_max - sdf['head']
        
        parts.append(sdf)
    
    df = pd.concat(parts, ignore_index=True)
    
    # Spatial features
    df['network_pressure_mean'] = df.groupby(['scenario_id', 'timestamp'])['pressure'].transform('mean')
    df['network_pressure_std'] = df.groupby(['scenario_id', 'timestamp'])['pressure'].transform('std')
    df['network_demand_mean'] = df.groupby(['scenario_id', 'timestamp'])['demand'].transform('mean')
    df['pressure_deviation'] = df['pressure'] - df['network_pressure_mean']
    df['demand_deviation'] = df.groupby('node_id')['demand'].transform(lambda x: x - x.mean())
    
    return df

def demo_scenario(scenario_id, model, metadata, dataset_dir="dataset"):
    """Demo leak detection on a scenario"""
    print_header(f"🔍 LEAK DETECTION DEMO - Scenario #{scenario_id}")
    
    # Load scenario data
    print_section("📂 Loading Scenario Data")
    scenario_dir = Path(dataset_dir) / f"scenario_{scenario_id:05d}"
    nodes_file = scenario_dir / "nodes.parquet"
    
    if not nodes_file.exists():
        print(f"❌ Scenario file not found: {nodes_file}")
        return None
    
    df = pd.read_parquet(nodes_file)
    print(f"✅ Loaded {len(df):,} data points")
    print(f"   • {df['node_id'].nunique()} nodes")
    print(f"   • {df['timestamp'].nunique()} timesteps")
    print(f"   • Duration: {df['timestamp'].max() / 3600:.1f} hours")
    
    # Get actual leaks info
    print_section("📋 Actual Leak Information")
    metadata_file = Path(dataset_dir) / "metadata.csv"
    if metadata_file.exists():
        meta_df = pd.read_csv(metadata_file)
        scenario_meta = meta_df[meta_df['scenario_id'] == scenario_id].iloc[0]
        
        if 'leak_nodes' in scenario_meta and pd.notna(scenario_meta['leak_nodes']):
            import ast
            leak_nodes = ast.literal_eval(scenario_meta['leak_nodes'])
            leak_starts = ast.literal_eval(scenario_meta['leak_start_times_s'])
            leak_ends = ast.literal_eval(scenario_meta['leak_end_times_s'])
            
            print(f"🚨 {len(leak_nodes)} leak(s) in this scenario:")
            for i, node in enumerate(leak_nodes):
                duration = (leak_ends[i] - leak_starts[i]) / 3600
                print(f"   {i+1}. Node {node}: {leak_starts[i]/3600:.1f}h - {leak_ends[i]/3600:.1f}h (duration: {duration:.1f}h)")
        else:
            leak_node = str(scenario_meta['leak_node'])
            leak_start = scenario_meta['start_time_s']
            leak_end = scenario_meta['end_time_s']
            duration = (leak_end - leak_start) / 3600
            print(f"🚨 1 leak in this scenario:")
            print(f"   Node {leak_node}: {leak_start/3600:.1f}h - {leak_end/3600:.1f}h (duration: {duration:.1f}h)")
            leak_nodes = [leak_node]
            leak_starts = [leak_start]
            leak_ends = [leak_end]
    
    # Prepare features
    print_section("⚙️  Feature Engineering")
    df = prepare_features(df, scenario_id)
    print(f"✅ Engineered {len(metadata['feature_cols'])} features")
    
    # Predict
    print_section("🤖 Running AI Model")
    feature_cols = metadata['feature_cols']
    X = df[feature_cols].values
    
    print("⏳ Computing leak probabilities...")
    y_proba = model.predict_proba(X)[:, 1]
    df['leak_probability'] = y_proba
    
    print(f"✅ Prediction complete!")
    print(f"   • Max probability: {y_proba.max():.4f}")
    print(f"   • Min probability: {y_proba.min():.4f}")
    print(f"   • Mean probability: {y_proba.mean():.4f}")
    
    # Top-K Analysis
    print_section("🎯 TOP-K LEAK LOCALIZATION")
    
    results = []
    for i, leak_node in enumerate(leak_nodes):
        t0, t1 = leak_starts[i], leak_ends[i]
        
        # Filter to leak time window
        leak_window = df[(df['timestamp'] >= t0) & (df['timestamp'] <= t1)]
        
        if len(leak_window) == 0:
            continue
        
        # Aggregate by node
        node_probs = leak_window.groupby('node_id')['leak_probability'].max().sort_values(ascending=False)
        
        # Top-5
        top5_nodes = node_probs.head(5).index.tolist()
        top5_probs = node_probs.head(5).values
        
        leak_node_str = str(leak_node)
        rank = None
        for r, node in enumerate(node_probs.index, 1):
            if str(node) == leak_node_str:
                rank = r
                break
        
        in_top5 = rank is not None and rank <= 5
        
        print(f"\n{'━'*70}")
        print(f"  LEAK #{i+1}: Node {leak_node} ({t0/3600:.1f}h - {t1/3600:.1f}h)")
        print(f"{'━'*70}")
        
        if in_top5:
            print(f"  ✅ FOUND! Ranked #{rank} out of {len(node_probs)} nodes")
        else:
            if rank:
                print(f"  ⚠️  Ranked #{rank} (not in top-5)")
            else:
                print(f"  ❌ Not detected")
        
        print(f"\n  📊 Top-5 Suspects:")
        for r, (node, prob) in enumerate(zip(top5_nodes, top5_probs), 1):
            marker = " ⭐ [ACTUAL LEAK]" if str(node) == leak_node_str else ""
            print(f"     {r}. Node {node:6s} → {prob:.4f}{marker}")
        
        results.append({
            'leak_node': leak_node,
            'rank': rank,
            'in_top5': in_top5,
            'top1_node': top5_nodes[0],
            'top1_prob': top5_probs[0]
        })
    
    # Summary
    print_section("📈 SUMMARY")
    top5_found = sum(1 for r in results if r['in_top5'])
    top1_found = sum(1 for r in results if r['rank'] == 1)
    
    print(f"  Total leaks: {len(results)}")
    print(f"  Top-1 Accuracy: {top1_found}/{len(results)} ({top1_found/len(results)*100:.1f}%)")
    print(f"  Top-5 Accuracy: {top5_found}/{len(results)} ({top5_found/len(results)*100:.1f}%)")
    
    if top5_found / len(results) >= 0.6:
        print(f"\n  🎉 EXCELLENT performance!")
    elif top5_found / len(results) >= 0.4:
        print(f"\n  ✅ GOOD performance!")
    elif top5_found / len(results) >= 0.2:
        print(f"\n  ⚠️  MODERATE performance")
    else:
        print(f"\n  ❌ POOR performance")
    
    print(f"\n  💡 Interpretation:")
    print(f"     With Top-5 accuracy of {top5_found/len(results)*100:.1f}%, field technicians")
    print(f"     only need to check 5 nodes (2.6% of network) instead of all 194 nodes")
    print(f"     → Saves {(1 - 5/194)*100:.1f}% inspection effort!")
    
    return results

def demo_multiple_scenarios(scenario_ids):
    """Demo on multiple scenarios"""
    model, metadata = load_model()
    if model is None:
        return
    
    all_results = []
    for scenario_id in scenario_ids:
        results = demo_scenario(scenario_id, model, metadata)
        if results:
            all_results.extend(results)
    
    # Overall summary
    if all_results:
        print_header("🏆 OVERALL PERFORMANCE")
        total = len(all_results)
        top1 = sum(1 for r in all_results if r['rank'] == 1)
        top5 = sum(1 for r in all_results if r['in_top5'])
        
        print(f"  Total leaks tested: {total}")
        print(f"  Top-1 Accuracy: {top1}/{total} ({top1/total*100:.1f}%)")
        print(f"  Top-5 Accuracy: {top5}/{total} ({top5/total*100:.1f}%)")
        print(f"\n  🎯 Model successfully localizes leaks to top-5 suspects")
        print(f"     in {top5/total*100:.1f}% of cases!")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Test specific scenarios
        scenario_ids = [int(x) for x in sys.argv[1:]]
        demo_multiple_scenarios(scenario_ids)
    else:
        # Demo on sample scenarios
        print("🎬 Running demo on sample scenarios...")
        print("   (Use: python scripts/demo_leak_detection.py <scenario_ids> for custom scenarios)")
        demo_multiple_scenarios([24, 30, 50, 52, 57])








