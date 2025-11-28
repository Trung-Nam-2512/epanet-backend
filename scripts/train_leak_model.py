"""
Pipeline training mô hình phát hiện rò rỉ
"""
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix
import pickle
import warnings
warnings.filterwarnings('ignore')

# CatBoost
try:
    from catboost import CatBoostClassifier
    CATBOOST_AVAILABLE = True
except ImportError:
    CATBOOST_AVAILABLE = False
    print("[WARNING] CatBoost not installed. Install: pip install catboost")

print("="*80)
print("TRAINING MO HINH PHAT HIEN RO RI")
print("="*80)

# 1. Load và Preprocess Data
print("\n1. LOAD VA PREPROCESS DATA:")
print("-" * 80)

dataset_dir = Path("dataset")
# Support cả old structure (file trực tiếp) và new structure (file trong subdir)
parquet_files_direct = sorted(dataset_dir.glob("scenario_*.parquet"))
parquet_files_subdir = []
for scenario_dir in sorted(dataset_dir.glob("scenario_*")):
    if scenario_dir.is_dir():
        # New structure: tìm nodes.parquet trong subdirectory
        nodes_file = scenario_dir / "nodes.parquet"
        if nodes_file.exists():
            parquet_files_subdir.append(nodes_file)
        # Hoặc tìm bất kỳ parquet nào trong subdir (fallback)
        elif not parquet_files_subdir:
            parquet_in_dir = list(scenario_dir.glob("*.parquet"))
            if parquet_in_dir:
                parquet_files_subdir.extend(parquet_in_dir)
parquet_files = sorted(parquet_files_direct + parquet_files_subdir)

if len(parquet_files) == 0:
    print("[ERROR] Khong tim thay parquet files trong dataset/")
    exit(1)

print(f"[OK] Tim thay {len(parquet_files)} scenarios")

# Load sample để check structure
df_sample = pd.read_parquet(parquet_files[0])
print(f"[OK] Sample shape: {df_sample.shape}")
print(f"[OK] Columns: {list(df_sample.columns)}")

# FIX: Tạm bỏ filter reservoir để tránh loại nhầm junction
# (Nếu có metadata node type từ INP thì nên dùng metadata đó)
# reservoir_nodes = df_sample[df_sample['demand'] < -0.1]['node_id'].unique().tolist()
# print(f"[INFO] Reservoir nodes: {reservoir_nodes}")

# Load tất cả data
print("\n[INFO] Dang load data...")
print("[INFO] Loading FULL dataset (all scenarios)")

# MEMORY LIMIT: Giảm số scenarios nếu bộ nhớ không đủ (28M records với 1500 scenarios)
# Với RAM hạn chế, train với 500 scenarios (~9.4M records) cho ổn định
max_scenarios = 500  # Giảm xuống 500 scenarios để tránh MemoryError (từ 28M -> ~9.4M records)
print(f"[INFO] Training với {max_scenarios if max_scenarios else 'ALL'} scenarios (memory efficient)")
files_to_load = parquet_files[:max_scenarios] if max_scenarios else parquet_files

dfs = []
import time
start_load_time = time.time()
for i, f in enumerate(files_to_load):
    dfs.append(pd.read_parquet(f))
    if (i + 1) % 100 == 0 or (i + 1) == len(files_to_load):
        elapsed = time.time() - start_load_time
        rate = (i + 1) / elapsed if elapsed > 0 else 0
        remaining = (len(files_to_load) - i - 1) / rate if rate > 0 else 0
        print(f"  Loaded {i+1}/{len(files_to_load)} files... ({elapsed:.1f}s, ~{remaining:.1f}s remaining)")

df_all = pd.concat(dfs, ignore_index=True)
print(f"[OK] Total records: {len(df_all):,}")

# FIX: Tạm bỏ filter reservoir để tránh loại nhầm junction
# print("\n[INFO] Filtering reservoir nodes...")
# df_ml = df_all[~df_all['node_id'].isin(reservoir_nodes)].copy()
df_ml = df_all.copy()
print(f"[OK] Using all records: {len(df_ml):,} records")
print(f"[OK] Total nodes: {df_ml['node_id'].nunique()}")

# 2. Correct Labeling: (node == leak_node) & (t in [t0, t1])
print("\n2. LABELING (node==leak_node & t in [t0,t1]):")
print("-" * 80)

# Load metadata
metadata = pd.read_csv(dataset_dir / "metadata.csv")
scenarios_in_data = df_ml['scenario_id'].unique()
metadata = metadata[metadata['scenario_id'].isin(scenarios_in_data)].copy()
metadata = metadata.sort_values('scenario_id')

# FIX: Chuẩn hóa tên cột metadata (support cả start_time_s/end_time_s và leak_start_time_s/leak_end_time_s)
if 'start_time_s' not in metadata.columns and 'leak_start_time_s' in metadata.columns:
    metadata['start_time_s'] = metadata['leak_start_time_s']
if 'end_time_s' not in metadata.columns and 'leak_end_time_s' in metadata.columns:
    metadata['end_time_s'] = metadata['leak_end_time_s']

print(f"[INFO] Processing {len(metadata)} scenarios for labeling...")

# Initialize labels
df_ml['has_leak'] = 0

# Old labeling for comparison (will be removed)
df_ml['has_leak_old'] = (df_ml['leak_demand'] > 0).astype(int)

# OPTIMIZED: Vectorized labeling for maximum speed (supports multiple leaks per scenario)
print("[INFO] Vectorizing labeling process...")
start_label_time = time.time()

# Check if metadata has multiple leaks per scenario (new format)
if 'leak_nodes' in metadata.columns and 'n_leaks' in metadata.columns:
    print("[INFO] Detected multiple leaks per scenario format")
    # Expand metadata to have one row per leak
    expanded_rows = []
    for _, row in metadata.iterrows():
        scenario_id = row['scenario_id']
        leak_nodes = eval(row['leak_nodes']) if isinstance(row['leak_nodes'], str) else row['leak_nodes']
        leak_start_times = eval(row['leak_start_times_s']) if isinstance(row['leak_start_times_s'], str) else row['leak_start_times_s']
        leak_end_times = eval(row['leak_end_times_s']) if isinstance(row['leak_end_times_s'], str) else row['leak_end_times_s']
        
        for i, leak_node in enumerate(leak_nodes):
            expanded_rows.append({
                'scenario_id': scenario_id,
                'leak_node': leak_node,
                'start_time_s': leak_start_times[i],
                'end_time_s': leak_end_times[i]
            })
    
    metadata_expanded = pd.DataFrame(expanded_rows)
    print(f"[INFO] Expanded {len(metadata)} scenarios to {len(metadata_expanded)} leak instances")
else:
    # Single leak per scenario (backward compatible)
    metadata_expanded = metadata[['scenario_id', 'leak_node', 'start_time_s', 'end_time_s']].copy()

# Convert leak info to dictionary for fast lookup (avoid huge merge)
print("[INFO] Building leak lookup dictionary...")
leak_lookup = {}
for _, row in metadata_expanded.iterrows():
    scenario_id = row['scenario_id']
    if scenario_id not in leak_lookup:
        leak_lookup[scenario_id] = []
    leak_lookup[scenario_id].append({
        'leak_node': str(int(float(row['leak_node']))) if '.' in str(row['leak_node']) else str(row['leak_node']),
        'start_time_s': row['start_time_s'],
        'end_time_s': row['end_time_s']
    })

# Convert node_id to string for comparison
df_ml['node_id_str'] = df_ml['node_id'].astype(str)

# Initialize label column
df_ml['has_leak'] = 0

print("[INFO] Labeling by scenario groups (optimized to avoid full scans)...")
# Group by scenario_id first to avoid repeated full scans
grouped = df_ml.groupby('scenario_id', sort=False)
total_scenarios = len(leak_lookup)
processed = 0

for scenario_id, scenario_df in grouped:
    processed += 1
    if processed % 50 == 0 or processed == total_scenarios:
        print(f"[INFO] Processed {processed}/{total_scenarios} scenarios...")
    
    # Get leak info for this scenario
    if scenario_id not in leak_lookup:
        continue
    
    scenario_leaks = leak_lookup[scenario_id]
    
    # Get indices for this scenario group
    scenario_indices = scenario_df.index
    
    # For each leak in this scenario
    for leak_info in scenario_leaks:
        # Find matching rows within this scenario: (node == leak_node) & (timestamp in [start, end])
        leak_mask = (
            (scenario_df['node_id_str'] == leak_info['leak_node']) &
            (scenario_df['timestamp'] >= leak_info['start_time_s']) &
            (scenario_df['timestamp'] <= leak_info['end_time_s'])
        )
        # Update only matching indices
        matching_indices = scenario_indices[leak_mask]
        if len(matching_indices) > 0:
            df_ml.loc[matching_indices, 'has_leak'] = 1

# Clean up temporary column
df_ml.drop(['node_id_str'], axis=1, inplace=True, errors='ignore')

elapsed = time.time() - start_label_time
print(f"[OK] Labeling completed in {elapsed:.1f}s (vectorized)")

# Compare old vs new labeling
leak_ratio_old = df_ml['has_leak_old'].mean()
leak_ratio_new = df_ml['has_leak'].mean()

print(f"[OK] Labeling comparison:")
print(f"  Old (leak_demand > 0): {df_ml['has_leak_old'].sum():,} ({100*leak_ratio_old:.4f}%)")
print(f"  New (exact leak_node): {df_ml['has_leak'].sum():,} ({100*leak_ratio_new:.4f}%)")
print(f"  [INFO] Using new labeling for training")

# 3. Feature Engineering
print("\n3. FEATURE ENGINEERING:")
print("-" * 80)

# Time features
df_ml['hour'] = (df_ml['timestamp'] / 3600).astype(int)
# REMOVED: hour_sin, hour_cos to prevent time-based bias
# Model should learn from hydraulic signals, not time-of-day patterns
# df_ml['hour_sin'] = np.sin(2 * np.pi * df_ml['hour'] / 24)
# df_ml['hour_cos'] = np.cos(2 * np.pi * df_ml['hour'] / 24)
print("[OK] Time features REMOVED to prevent time-based learning bias")

# Enhanced features: pressure changes, moving averages
print("[INFO] Adding enhanced features...")
print("[INFO] Optimizing with scenario-wise processing for memory efficiency...")
import time
feat_start = time.time()

# FIX: MEMORY EFFICIENT - Use groupby(['scenario_id', 'node_id']) with transform
# NO sorting needed, NO loop, pandas handles everything efficiently
print("[INFO] Computing features with groupby(['scenario_id', 'node_id']).transform()...")
print("[INFO] This is memory efficient and fast (single pass over data)...")

# Group by scenario_id AND node_id at once (ensures no leakage between scenarios)
g = df_ml.groupby(['scenario_id', 'node_id'], sort=False)

# Pressure/Head changes (diff within each scenario-node group)
print("  Computing pressure_change, head_change...")
df_ml['pressure_change'] = g['pressure'].transform(lambda x: x.diff().fillna(0))
df_ml['head_change'] = g['head'].transform(lambda x: x.diff().fillna(0))

# Moving averages (rolling within each scenario-node group)
print("  Computing moving averages (MA3, MA5)...")
df_ml['pressure_ma5'] = g['pressure'].transform(lambda x: x.rolling(5, min_periods=1).mean())
df_ml['head_ma5'] = g['head'].transform(lambda x: x.rolling(5, min_periods=1).mean())
df_ml['pressure_ma3'] = g['pressure'].transform(lambda x: x.rolling(3, min_periods=1).mean())
df_ml['head_ma3'] = g['head'].transform(lambda x: x.rolling(3, min_periods=1).mean())

# Pressure/Head drops (rolling max - current within each scenario-node group)
print("  Computing pressure_drop, head_drop...")
pressure_max = g['pressure'].transform(lambda x: x.rolling(5, min_periods=1).max())
head_max = g['head'].transform(lambda x: x.rolling(5, min_periods=1).max())
df_ml['pressure_drop'] = pressure_max - df_ml['pressure']
df_ml['head_drop'] = head_max - df_ml['head']

print(f"  [OK] Enhanced features completed in {time.time() - feat_start:.1f}s")

# Add SPATIAL features (network-level statistics - no topology needed!)
print("[INFO] Adding spatial features (network-level statistics)...")
spatial_start = time.time()

# Network-wide statistics at each timestep (captures global anomalies)
df_ml['network_pressure_mean'] = df_ml.groupby(['scenario_id', 'timestamp'])['pressure'].transform('mean')
df_ml['network_pressure_std'] = df_ml.groupby(['scenario_id', 'timestamp'])['pressure'].transform('std')
df_ml['network_demand_mean'] = df_ml.groupby(['scenario_id', 'timestamp'])['demand'].transform('mean')

# Node deviation from network (leak creates local anomalies)
df_ml['pressure_deviation'] = df_ml['pressure'] - df_ml['network_pressure_mean']
# FIX: Calculate demand_deviation per scenario to prevent leakage between train/val/test
df_ml['demand_deviation'] = df_ml.groupby(['scenario_id', 'node_id'])['demand'].transform(lambda x: x - x.mean())

print(f"  [OK] Spatial features completed in {time.time() - spatial_start:.1f}s")

# REMOVED: node_id_int, leak_node, scenario_id (to prevent data leakage)
print("[OK] REMOVED: node_id_int, leak_node, scenario_id from features")

# Feature columns (NO leak_node/scenario_id/node_id_int)
feature_cols = [
    'pressure', 'head', 'demand',
    # 'hour_sin', 'hour_cos',  # REMOVED: prevent time-based bias
    'pressure_ma3', 'pressure_ma5', 'head_ma3', 'head_ma5',
    'pressure_change', 'head_change',
    'pressure_drop', 'head_drop',
    # Spatial features (NEW - powerful for leak detection!)
    'network_pressure_mean', 'network_pressure_std', 'network_demand_mean',
    'pressure_deviation', 'demand_deviation'
]
print(f"[OK] Features: {len(feature_cols)} features")
print(f"  Features: {feature_cols}")

# 4. Train/Val/Test Split
print("\n4. TRAIN/VAL/TEST SPLIT:")
print("-" * 80)

# Stratified split by scenario để đảm bảo không leak giữa train/val/test
from sklearn.model_selection import train_test_split

# Split by scenario_id để tránh data leakage
scenario_ids = df_ml['scenario_id'].unique()
train_scenarios, temp_scenarios = train_test_split(
    scenario_ids, test_size=0.3, random_state=42
)
val_scenarios, test_scenarios = train_test_split(
    temp_scenarios, test_size=0.5, random_state=42
)

# OPTIMIZED: Use query() instead of isin() to avoid memory spike with boolean mask
# Convert to sets for fast lookup
train_scenarios_set = set(train_scenarios)
val_scenarios_set = set(val_scenarios)
test_scenarios_set = set(test_scenarios)

print("[INFO] Filtering datasets by scenario (using groupby to avoid memory spike)...")

# Process by groups to avoid creating large boolean masks
train_parts = []
val_parts = []
test_parts = []

for scenario_id, group_df in df_ml.groupby('scenario_id', sort=False):
    if scenario_id in train_scenarios_set:
        train_parts.append(group_df)
    elif scenario_id in val_scenarios_set:
        val_parts.append(group_df)
    elif scenario_id in test_scenarios_set:
        test_parts.append(group_df)

# OPTIMIZED: Extract features directly to avoid full DataFrame concat
# This reduces memory usage significantly
print("[INFO] Extracting features and labels (memory efficient)...")

X_train_parts = []
y_train_parts = []
X_val_parts = []
y_val_parts = []
X_test_parts = []
y_test_parts = []

for part in train_parts:
    X_train_parts.append(part[feature_cols])
    y_train_parts.append(part['has_leak'])

for part in val_parts:
    X_val_parts.append(part[feature_cols])
    y_val_parts.append(part['has_leak'])

# For test: also keep scenario_id and timestamp for per-scenario evaluation
test_meta_parts = []
for part in test_parts:
    X_test_parts.append(part[feature_cols])
    y_test_parts.append(part['has_leak'])
    # Keep metadata columns for evaluation
    test_meta_parts.append(part[['scenario_id', 'timestamp', 'node_id']])

# Concatenate only features and labels (much smaller than full DataFrame)
X_train = pd.concat(X_train_parts, ignore_index=True) if X_train_parts else pd.DataFrame()
y_train = pd.concat(y_train_parts, ignore_index=True) if y_train_parts else pd.Series()
X_val = pd.concat(X_val_parts, ignore_index=True) if X_val_parts else pd.DataFrame()
y_val = pd.concat(y_val_parts, ignore_index=True) if y_val_parts else pd.Series()
X_test = pd.concat(X_test_parts, ignore_index=True) if X_test_parts else pd.DataFrame()
y_test = pd.concat(y_test_parts, ignore_index=True) if y_test_parts else pd.Series()

# Concatenate test metadata for per-scenario evaluation
test_df_meta = pd.concat(test_meta_parts, ignore_index=True) if test_meta_parts else pd.DataFrame()

# Clean up to free memory
del train_parts, val_parts, test_parts
del X_train_parts, y_train_parts, X_val_parts, y_val_parts, X_test_parts, y_test_parts
del test_meta_parts

print(f"[OK] Train: {len(X_train):,} records ({len(train_scenarios)} scenarios)")
print(f"[OK] Val:   {len(X_val):,} records ({len(val_scenarios)} scenarios)")
print(f"[OK] Test:  {len(X_test):,} records ({len(test_scenarios)} scenarios)")

# 5. Normalization (SKIPPED for CatBoost - works better with original features)
print("\n5. NORMALIZATION:")
print("-" * 80)
print("[INFO] CatBoost works better with original features, skipping StandardScaler")
print("[INFO] Using original feature values")

# For CatBoost, use original features (no scaling needed)
X_train_scaled = X_train
X_val_scaled = X_val
X_test_scaled = X_test

# Keep scaler as None for consistency (but won't be used)
scaler = None

# 6. Handle Class Imbalance
print("\n6. HANDLE CLASS IMBALANCE:")
print("-" * 80)

# Check imbalance
print(f"[INFO] Class distribution:")
print(f"  No Leak: {(y_train == 0).sum():,} ({100*(y_train == 0).mean():.2f}%)")
print(f"  Leak:    {(y_train == 1).sum():,} ({100*(y_train == 1).mean():.2f}%)")

# FIX: Bỏ SMOTE cho CatBoost (SMOTE có thể tạo điểm phi vật lý cho dữ liệu thủy lực)
# CatBoost xử lý tốt class imbalance với class_weights
print("\n[INFO] Using class_weights for CatBoost (no SMOTE - avoids non-physical synthetic points)")
X_train_balanced = X_train_scaled
y_train_balanced = y_train
use_smote = False

# 7. Train Model
print("\n7. TRAINING MODEL:")
print("-" * 80)

if not CATBOOST_AVAILABLE:
    print("[ERROR] CatBoost not available!")
    print("  Install: pip install catboost")
    exit(1)

print("[INFO] Training CatBoostClassifier...")

# CatBoost parameters optimized for imbalanced data with spatial features
# HYBRID APPROACH: Increased capacity + better class weighting
# Calculate class weight (with higher multiplier for better recall)
base_weight = (len(y_train) - y_train.sum()) / y_train.sum() if y_train.sum() > 0 else 1.0
class_weight_multiplier = 15.0  # Increased from 10.0 to 15.0 (prioritize recall)
final_class_weight = min(1000.0, base_weight * class_weight_multiplier)  # Cap at 1000

print(f"[INFO] Class weight calculation (HYBRID - optimized):")
print(f"  Base ratio: {base_weight:.2f}")
print(f"  Multiplier: {class_weight_multiplier}x")
print(f"  Final weight: {final_class_weight:.2f}")

catboost_params = {
    'iterations': 1000,  # Increased from 500 (allow more learning)
    'learning_rate': 0.05,  # Good learning rate for gradual convergence
    'depth': 12,  # Increased from 10 (more complex patterns with spatial features)
    'loss_function': 'Logloss',
    'eval_metric': 'BalancedAccuracy',  # Better than PRAUC for imbalanced classification
    'random_seed': 42,
    'verbose': 100,
    'early_stopping_rounds': 100,  # Increased from 50 (more patient)
    'cat_features': [],  # No categorical features
    'class_weights': None if use_smote else [1.0, final_class_weight] if y_train.sum() > 0 else None,
    # Further reduced regularization for spatial features
    'l2_leaf_reg': 3,  # Reduced from 4 to 3 (spatial features need less regularization)
    'subsample': 0.85,  # Increased from 0.8 to 0.85
    'rsm': 0.95,  # Increased from 0.9 to 0.95 (use almost all features)
}

# Create CatBoost model
model = CatBoostClassifier(**catboost_params)

# Fit model
print("[INFO] Training with CatBoost...")
# Convert to numpy arrays for CatBoost (faster)
X_train_array = X_train_balanced.values if isinstance(X_train_balanced, pd.DataFrame) else X_train_balanced
X_val_array = X_val_scaled.values if isinstance(X_val_scaled, pd.DataFrame) else X_val_scaled
y_train_array = y_train_balanced.values if isinstance(y_train_balanced, pd.Series) else y_train_balanced

model.fit(
    X_train_array, y_train_array,
    eval_set=(X_val_array, y_val),
    use_best_model=True
)
print("[OK] Model trained!")

# 8. Evaluation
print("\n8. EVALUATION:")
print("-" * 80)

from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, roc_curve, fbeta_score, precision_recall_curve
)

# Get probabilities (convert to arrays if needed)
X_train_array = X_train_scaled.values if isinstance(X_train_scaled, pd.DataFrame) else X_train_scaled
X_val_array = X_val_scaled.values if isinstance(X_val_scaled, pd.DataFrame) else X_val_scaled
X_test_array = X_test_scaled.values if isinstance(X_test_scaled, pd.DataFrame) else X_test_scaled

y_train_proba = model.predict_proba(X_train_array)[:, 1]
y_val_proba = model.predict_proba(X_val_array)[:, 1]
y_test_proba = model.predict_proba(X_test_array)[:, 1]

# Optimize threshold based on PR-curve (F1/F2 or Precision@Recall)
print("\n[INFO] Optimizing threshold on validation set...")
print("  - Testing F1, F2 (beta=2), Precision@Recall metrics")

best_threshold = 0.5
best_metric_name = "F2"
best_metric_value = 0

# Priority: F2 (prioritize recall for leak detection)
# Search across full probability range (0.01 to 0.99) with finer granularity
print("  - Searching thresholds from 0.01 to 0.99...")
for threshold in np.arange(0.01, 0.99, 0.01):
    y_pred = (y_val_proba >= threshold).astype(int)
    if y_pred.sum() == 0:  # Skip if no positive predictions
        continue
    f2 = fbeta_score(y_val, y_pred, beta=2.0, zero_division=0)
    if f2 > best_metric_value:
        best_metric_value = f2
        best_threshold = threshold
        best_metric_name = "F2"

# Also try F1 for comparison (only if F2 is low)
if best_metric_value < 0.15:  # If F2 is very low, try F1
    print("  - F2 is low, also checking F1...")
    for threshold in np.arange(0.01, 0.99, 0.01):
        y_pred = (y_val_proba >= threshold).astype(int)
        if y_pred.sum() == 0:
            continue
        f1 = f1_score(y_val, y_pred, zero_division=0)
        if f1 > best_metric_value:
            best_metric_value = f1
            best_threshold = threshold
            best_metric_name = "F1"

# If still very low, try finer granularity at lower thresholds
if best_metric_value < 0.10:
    print("  [WARN] Low metric value, trying fine-grained lower thresholds...")
    for threshold in np.arange(0.001, 0.1, 0.001):
        y_pred = (y_val_proba >= threshold).astype(int)
        if y_pred.sum() == 0:
            continue
        f2 = fbeta_score(y_val, y_pred, beta=2.0, zero_division=0)
        if f2 > best_metric_value:
            best_metric_value = f2
            best_threshold = threshold
            best_metric_name = "F2"

print(f"[OK] Optimal threshold: {best_threshold:.4f} (optimized for {best_metric_name})")

# Predict with optimal threshold
y_train_pred = (y_train_proba >= best_threshold).astype(int)
y_val_pred = (y_val_proba >= best_threshold).astype(int)
y_test_pred = (y_test_proba >= best_threshold).astype(int)

# Metrics
train_acc = accuracy_score(y_train, y_train_pred)
train_prec = precision_score(y_train, y_train_pred, zero_division=0)
train_rec = recall_score(y_train, y_train_pred, zero_division=0)
train_f1 = f1_score(y_train, y_train_pred, zero_division=0)
train_f2 = fbeta_score(y_train, y_train_pred, beta=2.0, zero_division=0)

val_acc = accuracy_score(y_val, y_val_pred)
val_prec = precision_score(y_val, y_val_pred, zero_division=0)
val_rec = recall_score(y_val, y_val_pred, zero_division=0)
val_f1 = f1_score(y_val, y_val_pred, zero_division=0)
val_f2 = fbeta_score(y_val, y_val_pred, beta=2.0, zero_division=0)

test_acc = accuracy_score(y_test, y_test_pred)
test_prec = precision_score(y_test, y_test_pred, zero_division=0)
test_rec = recall_score(y_test, y_test_pred, zero_division=0)
test_f1 = f1_score(y_test, y_test_pred, zero_division=0)
test_f2 = fbeta_score(y_test, y_test_pred, beta=2.0, zero_division=0)

try:
    train_auc = roc_auc_score(y_train, y_train_proba)
    val_auc = roc_auc_score(y_val, y_val_proba)
    test_auc = roc_auc_score(y_test, y_test_proba)
except:
    train_auc = val_auc = test_auc = 0.0

print(f"\n{'Metric':<20} {'Train':<12} {'Val':<12} {'Test':<12}")
print("-"*60)
print(f"{'Accuracy':<20} {train_acc:<12.4f} {val_acc:<12.4f} {test_acc:<12.4f}")
print(f"{'Precision':<20} {train_prec:<12.4f} {val_prec:<12.4f} {test_prec:<12.4f}")
print(f"{'Recall':<20} {train_rec:<12.4f} {val_rec:<12.4f} {test_rec:<12.4f}")
print(f"{'F1-Score':<20} {train_f1:<12.4f} {val_f1:<12.4f} {test_f1:<12.4f}")
print(f"{'F-2.0 Score':<20} {train_f2:<12.4f} {val_f2:<12.4f} {test_f2:<12.4f}")
print(f"{'ROC-AUC':<20} {train_auc:<12.4f} {val_auc:<12.4f} {test_auc:<12.4f}")

# Classification Report
print("\n[INFO] Classification Report (Test Set):")
print("-" * 80)
print(classification_report(y_test, y_test_pred, target_names=['No Leak', 'Leak']))

# Per-scenario Top-K Evaluation (FIXED: filter by leak time window + fix indexing)
print("\n[INFO] Per-Scenario Top-K Evaluation (within leak time window):")
print("-" * 80)

test_metadata = metadata[metadata['scenario_id'].isin(test_scenarios)].copy()
top_k_scores = []
top1_scores = []
top10_scores = []  # Add Top-10 for complete evaluation
top_k = 5  # Default K

# FIX: Convert y_test_proba to array to ensure consistent indexing
y_test_proba_array = np.asarray(y_test_proba) if not isinstance(y_test_proba, np.ndarray) else y_test_proba
test_df_reset = test_df_meta.reset_index(drop=True)  # Use test_df_meta instead of test_df

for scenario_idx, (_, meta) in enumerate(test_metadata.iterrows()):
    scenario_id = int(meta['scenario_id'])
    leak_node = str(meta['leak_node'])
    start_time = float(meta['start_time_s'])
    end_time = float(meta['end_time_s'])
    
    # Normalize leak_node
    if '.' in leak_node:
        leak_node_normalized = str(int(float(leak_node)))
    else:
        leak_node_normalized = leak_node
    
    # FIX: Filter by leak time window FIRST
    scenario_mask = (
        (test_df_reset['scenario_id'] == scenario_id) &
        (test_df_reset['timestamp'] >= start_time) &
        (test_df_reset['timestamp'] <= end_time)
    )
    
    if scenario_mask.sum() == 0:
        continue
    
    # Get data within leak window
    scenario_data = test_df_reset[scenario_mask].copy()
    scenario_data_indices = scenario_data.index.values  # Array indices in reset DataFrame
    
    # FIX: Use correct indexing for probabilities
    if len(scenario_data_indices) > 0:
        scenario_proba = y_test_proba_array[scenario_data_indices]
    else:
        continue
    
    # Group by node_id and aggregate (max probability per node in leak window)
    scenario_data['proba'] = scenario_proba
    node_proba = scenario_data.groupby('node_id')['proba'].max().sort_values(ascending=False)
    
    if len(node_proba) == 0:
        continue
    
    # Get top-k nodes (Top-1, Top-5, Top-10)
    k = min(top_k, len(node_proba))
    k10 = min(10, len(node_proba))
    top_k_nodes = node_proba.head(k).index.astype(str).tolist()
    top10_nodes = node_proba.head(k10).index.astype(str).tolist()
    top1_node = str(node_proba.index[0]) if len(node_proba) > 0 else None
    
    # Check if leak_node is in top-k
    is_leak_in_topk = leak_node_normalized in top_k_nodes if top_k_nodes else False
    is_leak_in_top10 = leak_node_normalized in top10_nodes if top10_nodes else False
    is_leak_top1 = (top1_node == leak_node_normalized) if top1_node else False
    
    top_k_scores.append(is_leak_in_topk)
    top10_scores.append(is_leak_in_top10)
    top1_scores.append(is_leak_top1)
    
    if scenario_idx < 5:  # Show first 5 scenarios
        print(f"  Scenario {scenario_id}: Leak node '{leak_node_normalized}' "
              f"in top-{k}? {is_leak_in_topk} | top-10? {is_leak_in_top10} | top-1? {is_leak_top1}")

top_k_accuracy = np.mean(top_k_scores) if top_k_scores else 0.0
top10_accuracy = np.mean(top10_scores) if top10_scores else 0.0
top1_accuracy = np.mean(top1_scores) if top1_scores else 0.0
print(f"\n[OK] Top-1 Accuracy: {top1_accuracy:.4f} ({100*top1_accuracy:.2f}%)")
print(f"[OK] Top-5 Accuracy: {top_k_accuracy:.4f} ({100*top_k_accuracy:.2f}%)")
print(f"[OK] Top-10 Accuracy: {top10_accuracy:.4f} ({100*top10_accuracy:.2f}%)")

# Confusion Matrix
print("\n[INFO] Confusion Matrix (Test Set):")
print("-" * 80)
cm = confusion_matrix(y_test, y_test_pred)
print(f"                Predicted")
print(f"              No Leak   Leak")
print(f"Actual No Leak   {cm[0,0]:6d}  {cm[0,1]:6d}")
print(f"       Leak      {cm[1,0]:6d}  {cm[1,1]:6d}")

# Feature Importance
print("\n[INFO] Feature Importance:")
print("-" * 80)
feature_importance = pd.DataFrame({
    'feature': feature_cols,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)
print(feature_importance.to_string(index=False))
print(f"\n[INFO] Top 3 most important features:")
for i, row in feature_importance.head(3).iterrows():
    print(f"  {row['feature']}: {row['importance']:.6f}")

# 9. Save Model
print("\n9. SAVE MODEL:")
print("-" * 80)

model_dir = Path("models")
model_dir.mkdir(exist_ok=True)

# Save model
model_file = model_dir / "leak_detection_model.pkl"
with open(model_file, 'wb') as f:
    pickle.dump(model, f)
print(f"[OK] Model saved: {model_file}")

# Save scaler (if exists)
if scaler is not None:
    scaler_file = model_dir / "scaler.pkl"
    with open(scaler_file, 'wb') as f:
        pickle.dump(scaler, f)
    print(f"[OK] Scaler saved: {scaler_file}")
else:
    print("[INFO] No scaler (CatBoost uses original features)")

# Check if best threshold was found
try:
    best_threshold
except:
    best_threshold = 0.5

# Save metadata
# Note: reservoir_nodes not defined (filter removed to avoid misclassification)
model_metadata = {
    'feature_cols': feature_cols,
    'reservoir_nodes': [],  # Not filtered (temporarily removed to avoid misclassification)
    'n_train': len(X_train),
    'n_val': len(X_val),
    'n_test': len(X_test),
    'train_acc': float(train_acc),
    'train_prec': float(train_prec),
    'train_rec': float(train_rec),
    'train_f1': float(train_f1),
    'train_f2': float(train_f2),
    'val_acc': float(val_acc),
    'val_prec': float(val_prec),
    'val_rec': float(val_rec),
    'val_f1': float(val_f1),
    'val_f2': float(val_f2),
    'test_acc': float(test_acc),
    'test_prec': float(test_prec),
    'test_rec': float(test_rec),
    'test_f1': float(test_f1),
    'test_f2': float(test_f2),
    'test_auc': float(test_auc),
    'top_k_accuracy': float(top_k_accuracy),  # Top-5
    'top10_accuracy': float(top10_accuracy),  # Top-10
    'top1_accuracy': float(top1_accuracy),  # Top-1
    'use_smote': use_smote,
    'best_threshold': float(best_threshold),
    'best_metric': best_metric_name,
    'labeling_method': 'exact_leak_node_in_time_window'
}

import json
metadata_file = model_dir / "model_metadata.json"
with open(metadata_file, 'w') as f:
    json.dump(model_metadata, f, indent=2)
print(f"[OK] Metadata saved: {metadata_file}")

print("\n" + "="*80)
print("TRAINING HOAN TAT!")
print("="*80)
print("\nCac file da luu:")
print(f"  1. {model_file} - Model")
if scaler is not None:
    print(f"  2. {scaler_file} - Scaler")
else:
    print(f"  2. No scaler saved (CatBoost uses original features)")
print(f"  3. {metadata_file} - Metadata")
print("\nDe su dung model:")
print("  python scripts/predict_leak.py <scenario_id>")

