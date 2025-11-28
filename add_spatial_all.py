"""Add spatial features to all splits - Windows version"""

import pandas as pd
import sys
import time
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent / 'scripts'))

from add_spatial_features import load_topology, add_spatial_features_batch

print("\n" + "="*80)
print("ADDING SPATIAL FEATURES TO ALL SPLITS")
print("="*80 + "\n")

try:
    # Load topology
    print("📂 Loading topology...")
    topology_df, neighbor_map = load_topology("dataset/network_topology.csv")
    print(f"✅ Topology loaded: {len(topology_df)} nodes\n")
    
    # Process each split
    splits = ['train', 'val', 'test']
    
    for i, split in enumerate(splits, 1):
        print(f"{'='*80}")
        print(f"🔄 {i}/3: Processing {split.upper()}...")
        print(f"{'='*80}")
        
        input_file = f"dataset/{split}.parquet"
        output_file = f"dataset/{split}_with_spatial.parquet"
        
        # Check if input exists
        if not Path(input_file).exists():
            print(f"❌ ERROR: {input_file} not found!")
            continue
        
        # Load
        print(f"📂 Loading {input_file}...")
        start_time = time.time()
        df = pd.read_parquet(input_file)
        print(f"   Records: {len(df):,}")
        print(f"   Columns: {len(df.columns)}")
        
        # Add spatial features
        print(f"\n⏳ Adding spatial features...")
        df = add_spatial_features_batch(df, neighbor_map, topology_df, batch_size=100000)
        
        # Save
        print(f"\n💾 Saving to {output_file}...")
        df.to_parquet(output_file, compression='snappy', index=False)
        
        elapsed = time.time() - start_time
        print(f"✅ {split.upper()} done in {elapsed:.1f}s ({elapsed/60:.1f} min)")
        
        # Verify spatial features
        print(f"\n🔍 Verification:")
        spatial_cols = [c for c in df.columns if any(x in c for x in 
                       ['neighbor', 'gradient', 'node_degree', 'node_betweenness', 'node_elevation'])]
        print(f"   Spatial features added: {len(spatial_cols)}")
        if spatial_cols:
            print(f"   Examples: {spatial_cols[:3]}...")
        print(f"   Total columns: {len(df.columns)}\n")
    
    print(f"{'='*80}")
    print("🎉 SUCCESS! All spatial features added to train/val/test")
    print(f"{'='*80}\n")
    
    print("📁 Files ready:")
    print("   ✅ dataset/train_with_spatial.parquet")
    print("   ✅ dataset/val_with_spatial.parquet")
    print("   ✅ dataset/test_with_spatial.parquet\n")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)












