"""
Sử dụng model đã train để predict leak
"""
import pandas as pd
import numpy as np
import pickle
import sys
from pathlib import Path

def load_model():
    """Load model và scaler"""
    model_dir = Path("models")
    model_file = model_dir / "leak_detection_model.pkl"
    scaler_file = model_dir / "scaler.pkl"
    metadata_file = model_dir / "model_metadata.json"
    
    if not model_file.exists():
        print(f"[ERROR] Model file not found: {model_file}")
        print("        Please train model first: python scripts/train_leak_model.py")
        return None, None, None
    
    with open(model_file, 'rb') as f:
        model = pickle.load(f)
    
    with open(scaler_file, 'rb') as f:
        scaler = pickle.load(f)
    
    import json
    with open(metadata_file, 'r') as f:
        metadata = json.load(f)
    
    return model, scaler, metadata

def predict_scenario(scenario_id, dataset_dir="dataset"):
    """Predict leak cho một scenario"""
    # Load model
    model, scaler, metadata = load_model()
    if model is None:
        return
    
    # Load scenario data
    scenario_file = Path(dataset_dir) / f"scenario_{scenario_id:05d}.parquet"
    if not scenario_file.exists():
        print(f"[ERROR] Scenario file not found: {scenario_file}")
        return
    
    df = pd.read_parquet(scenario_file)
    
    # Filter reservoir nodes
    reservoir_nodes = metadata['reservoir_nodes']
    df_ml = df[~df['node_id'].isin(reservoir_nodes)].copy()
    
    # Feature engineering
    df_ml['hour'] = (df_ml['timestamp'] / 3600).astype(int)
    df_ml['hour_sin'] = np.sin(2 * np.pi * df_ml['hour'] / 24)
    df_ml['hour_cos'] = np.cos(2 * np.pi * df_ml['hour'] / 24)
    
    # Node ID encoding (same as training)
    from sklearn.preprocessing import LabelEncoder
    le = LabelEncoder()
    le.fit(df_ml['node_id'].astype(str))
    df_ml['node_id_int'] = le.transform(df_ml['node_id'].astype(str))
    
    # Prepare features
    feature_cols = metadata['feature_cols']
    X = df_ml[feature_cols]
    X_scaled = pd.DataFrame(
        scaler.transform(X),
        columns=feature_cols,
        index=X.index
    )
    
    # Predict
    predictions = model.predict(X_scaled)
    probabilities = model.predict_proba(X_scaled)[:, 1]  # Probability of leak
    
    # Add predictions to dataframe
    df_ml['predicted_leak'] = predictions
    df_ml['leak_probability'] = probabilities
    
    # Results
    print("="*80)
    print(f"PREDICTION RESULTS - Scenario {scenario_id}")
    print("="*80)
    
    leak_predictions = df_ml[df_ml['predicted_leak'] == 1]
    if len(leak_predictions) > 0:
        print(f"\n[INFO] Detected {len(leak_predictions)} records with leak")
        print("\nTop 10 highest probability leaks:")
        top_leaks = leak_predictions.nlargest(10, 'leak_probability')[
            ['timestamp', 'node_id', 'pressure', 'head', 'leak_probability', 'leak_demand']
        ]
        print(top_leaks.to_string(index=False))
    else:
        print("\n[INFO] No leaks predicted")
    
    # Compare with actual
    if 'leak_demand' in df_ml.columns:
        actual_leaks = df_ml[df_ml['leak_demand'] > 0]
        print(f"\n[INFO] Actual leaks in data: {len(actual_leaks)} records")
        
        if len(leak_predictions) > 0 and len(actual_leaks) > 0:
            # Check overlap
            overlap = df_ml[
                (df_ml['predicted_leak'] == 1) & 
                (df_ml['leak_demand'] > 0)
            ]
            print(f"[INFO] Correct predictions: {len(overlap)}/{len(actual_leaks)}")
    
    return df_ml

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/predict_leak.py <scenario_id>")
        print("Example: python scripts/predict_leak.py 1")
        sys.exit(1)
    
    scenario_id = int(sys.argv[1])
    predict_scenario(scenario_id)

