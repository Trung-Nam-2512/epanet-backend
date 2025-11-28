#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Post-processing rules for leak detection
Filter false positives using temporal and spatial consistency
"""
import pandas as pd
import numpy as np
from sklearn.metrics import precision_score, recall_score, fbeta_score, f1_score

def filter_temporal_consistency(predictions, min_consecutive=3):
    """
    Filter predictions: Chỉ giữ leak kéo dài ít nhất min_consecutive timesteps
    
    Rationale:
    - Real leaks persist for multiple timesteps (at least 3-5 timesteps = 45-75 minutes)
    - Isolated false positives (1 timestep) should be filtered out
    
    Parameters:
    ----------
    predictions : DataFrame
        DataFrame với columns ['scenario_id', 'node_id', 'timestamp', 'prediction']
    min_consecutive : int, default=3
        Số timesteps liên tiếp tối thiểu
    
    Returns:
    -------
    DataFrame
        DataFrame đã filter với column 'filtered_prediction'
    """
    print(f"[INFO] Applying temporal consistency filter (min_consecutive={min_consecutive})...")
    
    # Sort by scenario, node, timestamp
    predictions = predictions.sort_values(['scenario_id', 'node_id', 'timestamp']).copy()
    
    # Initialize
    predictions['consecutive_count'] = 0
    predictions['filtered_prediction'] = 0
    
    # Group by scenario và node
    for (scenario_id, node_id), group in predictions.groupby(['scenario_id', 'node_id']):
        # Sort by timestamp
        group = group.sort_values('timestamp')
        indices = group.index
        preds = group['prediction'].values
        
        # Calculate consecutive leak predictions
        consecutive = 0
        consecutive_counts = []
        
        for pred in preds:
            if pred == 1:
                consecutive += 1
            else:
                consecutive = 0
            consecutive_counts.append(consecutive)
        
        # Update dataframe
        predictions.loc[indices, 'consecutive_count'] = consecutive_counts
        
        # Filter: Keep only if consecutive >= min_consecutive
        filtered = np.where(np.array(consecutive_counts) >= min_consecutive, 1, 0)
        predictions.loc[indices, 'filtered_prediction'] = filtered
    
    # Stats
    original_leaks = (predictions['prediction'] == 1).sum()
    filtered_leaks = (predictions['filtered_prediction'] == 1).sum()
    removed = original_leaks - filtered_leaks
    
    print(f"  Original leak predictions: {original_leaks:,}")
    print(f"  After filter: {filtered_leaks:,}")
    print(f"  Removed (isolated): {removed:,} ({100*removed/original_leaks:.1f}%)")
    
    return predictions


def filter_spatial_consistency(predictions, df_ml, pressure_threshold=0.5):
    """
    Filter predictions: Kiểm tra pressure drop tại node
    
    Rationale:
    - Real leaks cause significant pressure drop (high pressure_deviation)
    - False positives often have small pressure deviations
    
    Parameters:
    ----------
    predictions : DataFrame
        DataFrame với columns ['scenario_id', 'node_id', 'timestamp', 'prediction']
    df_ml : DataFrame
        DataFrame gốc với pressure_deviation
    pressure_threshold : float, default=0.5
        Threshold cho pressure deviation (normalized)
    
    Returns:
    -------
    DataFrame
        DataFrame đã filter với column 'filtered_prediction'
    """
    print(f"[INFO] Applying spatial consistency filter (pressure_threshold={pressure_threshold})...")
    
    # Merge với df_ml để có pressure_deviation
    predictions = predictions.merge(
        df_ml[['scenario_id', 'node_id', 'timestamp', 'pressure_deviation']],
        on=['scenario_id', 'node_id', 'timestamp'],
        how='left'
    )
    
    # Rule: Chỉ giữ nếu pressure_deviation đủ lớn (absolute value)
    predictions['filtered_prediction'] = np.where(
        (predictions['prediction'] == 1) & 
        (predictions['pressure_deviation'].abs() > pressure_threshold),
        1,
        0
    )
    
    # Stats
    original_leaks = (predictions['prediction'] == 1).sum()
    filtered_leaks = (predictions['filtered_prediction'] == 1).sum()
    removed = original_leaks - filtered_leaks
    
    print(f"  Original leak predictions: {original_leaks:,}")
    print(f"  After filter: {filtered_leaks:,}")
    print(f"  Removed (low pressure deviation): {removed:,} ({100*removed/original_leaks:.1f}%)")
    
    return predictions


def filter_combined(predictions, df_ml, min_consecutive=3, pressure_threshold=0.5):
    """
    Filter predictions: Kết hợp temporal và spatial consistency
    
    Parameters:
    ----------
    predictions : DataFrame
        DataFrame với columns ['scenario_id', 'node_id', 'timestamp', 'prediction']
    df_ml : DataFrame
        DataFrame gốc với pressure_deviation
    min_consecutive : int, default=3
        Số timesteps liên tiếp tối thiểu
    pressure_threshold : float, default=0.5
        Threshold cho pressure deviation
    
    Returns:
    -------
    DataFrame
        DataFrame đã filter với column 'filtered_prediction'
    """
    print("[INFO] Applying combined (temporal + spatial) filter...")
    
    # Apply temporal rule first
    predictions = filter_temporal_consistency(predictions.copy(), min_consecutive)
    
    # Apply spatial rule on temporal-filtered results
    predictions['prediction'] = predictions['filtered_prediction']
    predictions = filter_spatial_consistency(predictions, df_ml, pressure_threshold)
    
    return predictions


def evaluate_filtered(y_true, y_pred_original, y_pred_filtered):
    """
    Evaluate metrics before and after filtering
    
    Parameters:
    ----------
    y_true : array-like
        True labels
    y_pred_original : array-like
        Original predictions (before filtering)
    y_pred_filtered : array-like
        Filtered predictions (after post-processing)
    
    Returns:
    -------
    dict
        Dictionary with metrics
    """
    # Original metrics
    precision_orig = precision_score(y_true, y_pred_original, zero_division=0)
    recall_orig = recall_score(y_true, y_pred_original, zero_division=0)
    f1_orig = f1_score(y_true, y_pred_original, zero_division=0)
    f2_orig = fbeta_score(y_true, y_pred_original, beta=2.0, zero_division=0)
    
    # Filtered metrics
    precision_filt = precision_score(y_true, y_pred_filtered, zero_division=0)
    recall_filt = recall_score(y_true, y_pred_filtered, zero_division=0)
    f1_filt = f1_score(y_true, y_pred_filtered, zero_division=0)
    f2_filt = fbeta_score(y_true, y_pred_filtered, beta=2.0, zero_division=0)
    
    results = {
        'original': {
            'precision': precision_orig,
            'recall': recall_orig,
            'f1': f1_orig,
            'f2': f2_orig
        },
        'filtered': {
            'precision': precision_filt,
            'recall': recall_filt,
            'f1': f1_filt,
            'f2': f2_filt
        },
        'improvement': {
            'precision': precision_filt - precision_orig,
            'recall': recall_filt - recall_orig,
            'f1': f1_filt - f1_orig,
            'f2': f2_filt - f2_orig
        }
    }
    
    return results


def print_evaluation_results(results):
    """
    Print evaluation results in a nice format
    """
    print("\n" + "=" * 80)
    print("POST-PROCESSING EVALUATION RESULTS")
    print("=" * 80)
    
    print("\nOriginal (Before Post-processing):")
    print(f"  Precision: {results['original']['precision']:.4f} ({100*results['original']['precision']:.2f}%)")
    print(f"  Recall:    {results['original']['recall']:.4f} ({100*results['original']['recall']:.2f}%)")
    print(f"  F1-Score:  {results['original']['f1']:.4f}")
    print(f"  F2-Score:  {results['original']['f2']:.4f}")
    
    print("\nFiltered (After Post-processing):")
    print(f"  Precision: {results['filtered']['precision']:.4f} ({100*results['filtered']['precision']:.2f}%)")
    print(f"  Recall:    {results['filtered']['recall']:.4f} ({100*results['filtered']['recall']:.2f}%)")
    print(f"  F1-Score:  {results['filtered']['f1']:.4f}")
    print(f"  F2-Score:  {results['filtered']['f2']:.4f}")
    
    print("\nImprovement:")
    print(f"  Precision: {results['improvement']['precision']:+.4f} ({100*results['improvement']['precision']:+.2f}%)")
    print(f"  Recall:    {results['improvement']['recall']:+.4f} ({100*results['improvement']['recall']:+.2f}%)")
    print(f"  F1-Score:  {results['improvement']['f1']:+.4f}")
    print(f"  F2-Score:  {results['improvement']['f2']:+.4f}")
    
    print("\n" + "=" * 80)
















