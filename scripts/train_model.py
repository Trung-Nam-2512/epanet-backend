"""
Standalone training script for leak detection model
Can run on server without Jupyter notebook
"""
import os
import sys
import yaml
import time
import json
import pickle
import warnings
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, 
    roc_auc_score, confusion_matrix, classification_report
)

warnings.filterwarnings('ignore')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def load_config(config_path='config/training_config.yaml'):
    """Load training configuration"""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def compute_fbeta_score(y_true, y_pred, beta=2.0):
    """Compute F-beta score"""
    from sklearn.metrics import fbeta_score
    return fbeta_score(y_true, y_pred, beta=beta, zero_division=0)

def main():
    print("="*80)
    print("EPANET LEAK DETECTION - MODEL TRAINING")
    print("="*80)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Load config
    config = load_config()
    print(f"\n✅ Loaded config from config/training_config.yaml")
    
    # Change to project root
    os.chdir(project_root)
    print(f"📂 Working directory: {os.getcwd()}")
    
    # Import training logic from consolidated notebook
    # For now, print instruction to run notebook
    print("\n" + "="*80)
    print("TRAINING OPTIONS:")
    print("="*80)
    print("\n1. Run Jupyter notebook (recommended for first run):")
    print("   jupyter nbconvert --to notebook --execute \\")
    print("       notebooks/train_leak_detection.ipynb \\")
    print("       --output train_leak_detection_output.ipynb")
    
    print("\n2. Or follow these steps manually:")
    print("   - Load dataset from dataset/")
    print("   - Preprocess & engineer features")
    print("   - Train CatBoost model")
    print("   - Evaluate on test set")
    print("   - Save model to models/")
    
    print("\n📌 Config highlights:")
    print(f"   Undersampling: {config['preprocessing']['use_undersampling']}")
    print(f"   Target ratio: {config['preprocessing']['target_imbalance_ratio']}:1")
    print(f"   Model: {config['model']['type']}")
    print(f"   GPU: {config['model']['catboost']['use_gpu']}")
    print(f"   SMOTE: {config['advanced']['use_smote']} (not needed with new dataset)")
    print(f"   Post-processing filters: {config['post_processing']['apply_temporal_filter']} (disabled - hurts recall)")
    
    print("\n" + "="*80)
    print("⚠️  This is a placeholder script.")
    print("    Please run the Jupyter notebook for full training pipeline.")
    print("="*80)

if __name__ == "__main__":
    main()










