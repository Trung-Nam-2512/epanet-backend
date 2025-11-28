"""
Quick check: Is system ready to train?
"""
import psutil
import os
from pathlib import Path

print("="*70)
print("🔍 PRE-TRAINING CHECKLIST")
print("="*70)

# 1. Check RAM
mem = psutil.virtual_memory()
available_gb = mem.available / (1024**3)
total_gb = mem.total / (1024**3)

print(f"\n1️⃣  RAM Check:")
print(f"   Total: {total_gb:.1f} GB")
print(f"   Available: {available_gb:.1f} GB ({100-mem.percent:.1f}% free)")

if available_gb >= 10:
    print(f"   ✅ EXCELLENT - Can use 2000+ scenarios")
    recommended = "None  # Use all"
elif available_gb >= 7:
    print(f"   ✅ GOOD - Can use 1500-2000 scenarios")
    recommended = "1800"
elif available_gb >= 5:
    print(f"   ⚠️  OK - Can use 1000-1500 scenarios")
    recommended = "1500"
else:
    print(f"   ❌ LOW - Can only use 800-1000 scenarios")
    recommended = "1000"

print(f"   💡 Recommended: max_scenarios = {recommended}")

# 2. Check dataset
print(f"\n2️⃣  Dataset Check:")
dataset_path = Path("dataset")
if not dataset_path.exists():
    print(f"   ❌ dataset/ not found!")
else:
    labels_path = dataset_path / "labels.csv"
    if labels_path.exists():
        with open(labels_path) as f:
            lines = f.readlines()
        leaks = len(lines) - 1  # -1 for header
        print(f"   ✅ labels.csv: {leaks:,} leaks")
    
    scenarios = [d for d in os.listdir(dataset_path) if d.startswith("scenario_")]
    print(f"   ✅ Scenarios: {len(scenarios):,} folders")

# 3. Check notebook
print(f"\n3️⃣  Notebook Check:")
notebook_path = Path("notebooks/train_leak_detection.ipynb")
if not notebook_path.exists():
    print(f"   ❌ Notebook not found!")
else:
    print(f"   ✅ Notebook exists")
    # Check if fixes applied
    import json
    with open(notebook_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    
    has_memory_check = False
    has_no_filters = False
    
    for cell in nb['cells']:
        if cell['cell_type'] != 'code':
            continue
        source = ''.join(cell['source']) if isinstance(cell['source'], list) else cell['source']
        
        if 'MEMORY SAFETY' in source or 'available_gb' in source:
            has_memory_check = True
        
        if '# predictions_df = filter_temporal' in source or \
           '# predictions_df_ensemble = filter_temporal' in source:
            has_no_filters = True
    
    if has_memory_check:
        print(f"   ✅ Memory safety check: ENABLED")
    else:
        print(f"   ⚠️  Memory safety check: NOT FOUND")
    
    if has_no_filters:
        print(f"   ✅ Post-processing filters: DISABLED (good!)")
    else:
        print(f"   ⚠️  Post-processing filters: May still be active")

# 4. Check dependencies
print(f"\n4️⃣  Dependencies Check:")
try:
    import pandas
    print(f"   ✅ pandas: {pandas.__version__}")
except ImportError:
    print(f"   ❌ pandas not installed")

try:
    import catboost
    print(f"   ✅ catboost: {catboost.__version__}")
except ImportError:
    print(f"   ❌ catboost not installed")

try:
    import sklearn
    print(f"   ✅ scikit-learn: {sklearn.__version__}")
except ImportError:
    print(f"   ❌ scikit-learn not installed")

# 5. GPU check
print(f"\n5️⃣  GPU Check:")
import subprocess
try:
    result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, timeout=5)
    if result.returncode == 0:
        print(f"   ✅ GPU detected")
        for line in result.stdout.split('\n'):
            if 'GeForce' in line or 'RTX' in line:
                print(f"   💻 {line.strip()}")
    else:
        print(f"   ℹ️  No GPU - will use CPU (slower)")
except:
    print(f"   ℹ️  No GPU - will use CPU (slower)")

# Summary
print(f"\n{'='*70}")
print(f"📋 SUMMARY")
print(f"{'='*70}")

if available_gb >= 5 and dataset_path.exists() and notebook_path.exists():
    print(f"✅ READY TO TRAIN!")
    print(f"\n📝 Recommended settings:")
    print(f"   max_scenarios = {recommended}")
    if available_gb < 8:
        print(f"\n⚠️  IMPORTANT: Close all other apps before training!")
        print(f"   - Close browsers (Chrome, Edge)")
        print(f"   - Close IDEs if not needed")
        print(f"   - Restart computer if possible")
else:
    print(f"❌ NOT READY - Please fix issues above")

print(f"{'='*70}")










