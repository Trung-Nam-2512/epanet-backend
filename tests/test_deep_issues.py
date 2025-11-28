"""
Test script để verify các vấn đề tiềm ẩn đã phát hiện
"""
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any

print("="*80)
print("DEEP AUDIT - TEST CAC VAN DE TIEM AN")
print("="*80)

# Test 1: Verify time-series application
print("\n[TEST 1] Time-Series Application")
print("-"*80)

try:
    from services.scada_boundary_service import scada_boundary_service
    import wntr
    from core.config import settings
    
    # Load model
    wn = wntr.network.WaterNetworkModel(settings.epanet_input_file)
    reservoir = wn.get_node("TXU2")
    
    initial_head = reservoir.base_head
    print(f"Initial base_head: {initial_head}m")
    
    # Create mock SCADA data với time-series
    scada_data = {
        "13085": [
            {"timestamp": "2025-01-15 10:00", "pressure": 20.0},
            {"timestamp": "2025-01-15 11:00", "pressure": 30.0},
            {"timestamp": "2025-01-15 12:00", "pressure": 25.0}
        ]
    }
    
    # Apply SCADA boundary
    applied = scada_boundary_service.apply_scada_boundary_conditions(
        wn=wn,
        scada_boundary_data=scada_data,
        simulation_duration_hours=3,
        hydraulic_timestep_hours=1
    )
    
    final_head = reservoir.base_head
    print(f"Final base_head: {final_head}m")
    
    # Check: Neu dung average, se la (20+30+25)/3 = 25.0
    # Neu dung time-series, se khac
    if abs(final_head - 25.0) < 0.1:
        print("[ISSUE] Code dang dung AVERAGE head (25.0m) thay vi time-series")
        print("   Expected: Time-varying head (20m, 30m, 25m)")
        print("   Actual: Constant average head (25.0m)")
    else:
        print("[OK] Head khong phai average - co the da dung time-series")
    
except Exception as e:
    print(f"[ERROR] Test failed: {e}")

# Test 2: Verify pressure vs head
print("\n[TEST 2] Pressure vs Head Conversion")
print("-"*80)

try:
    # Check config
    config_file = Path("config/scada_mapping.json")
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    station = config['scada_stations']['13085']
    mapping = station.get('epanet_mapping', {})
    
    print(f"apply_pressure_as_head: {mapping.get('apply_pressure_as_head')}")
    print(f"pressure_unit: {config.get('data_processing', {}).get('pressure_unit')}")
    
    # Check if co elevation config
    if 'elevation' not in mapping:
        print("[ISSUE] Khong co elevation config - khong ro pressure la absolute hay gauge")
        print("   Can xac dinh: SCADA pressure la absolute head hay gauge pressure?")
    else:
        print(f"[OK] Elevation config: {mapping.get('elevation')}")
    
except Exception as e:
    print(f"[ERROR] Test failed: {e}")

# Test 3: Verify time synchronization
print("\n[TEST 3] Time Synchronization")
print("-"*80)

try:
    # Check code logic
    code_file = Path("services/scada_boundary_service.py")
    with open(code_file, 'r', encoding='utf-8') as f:
        code = f.read()
    
    if 'datetime.now()' in code:
        print("[ISSUE] Code dang dung datetime.now() cho simulation start")
        print("   Van de: SCADA data co the tu qua khu")
        print("   Can: Sync voi SCADA data time hoac request time")
    else:
        print("[OK] Khong dung datetime.now()")
    
    # Check if co simulation_start_time parameter
    if 'simulation_start_time' in code:
        print("[OK] Co simulation_start_time parameter")
    else:
        print("[ISSUE] Khong co simulation_start_time parameter")
        print("   Can: Them parameter de sync time")
    
except Exception as e:
    print(f"[ERROR] Test failed: {e}")

# Test 4: Verify head_timeseries usage
print("\n[TEST 4] WNTR head_timeseries Usage")
print("-"*80)

try:
    import wntr
    from core.config import settings
    
    wn = wntr.network.WaterNetworkModel(settings.epanet_input_file)
    reservoir = wn.get_node("TXU2")
    
    # Check if head_timeseries exists
    if hasattr(reservoir, 'head_timeseries'):
        print("[OK] WNTR co head_timeseries attribute")
        print(f"   Type: {type(reservoir.head_timeseries)}")
        
        # Check if code uses it
        code_file = Path("services/scada_boundary_service.py")
        with open(code_file, 'r', encoding='utf-8') as f:
            code = f.read()
        
        if 'head_timeseries' in code:
            if 'TODO' in code or 'approximation' in code:
                print("[ISSUE] Code co TODO ve head_timeseries - chua implement dung")
            else:
                print("[OK] Code co su dung head_timeseries")
        else:
            print("[ISSUE] Code KHONG su dung head_timeseries")
            print("   Chi dung base_head (constant)")
    else:
        print("[ERROR] WNTR khong co head_timeseries")
    
except Exception as e:
    print(f"[ERROR] Test failed: {e}")

# Test 5: Verify validation
print("\n[TEST 5] Validation and Error Handling")
print("-"*80)

try:
    code_file = Path("services/scada_boundary_service.py")
    with open(code_file, 'r', encoding='utf-8') as f:
        code = f.read()
    
    # Check for validation
    validation_keywords = ['validate', 'check', 'range', 'min', 'max', 'error']
    has_validation = any(kw in code.lower() for kw in validation_keywords)
    
    if has_validation:
        print("[OK] Code co mot so validation")
    else:
        print("[ISSUE] Code thieu validation")
        print("   Can: Validate pressure values, time differences, etc.")
    
    # Check for error handling
    if 'try:' in code and 'except' in code:
        print("[OK] Code co error handling")
    else:
        print("[ISSUE] Code thieu error handling")
    
except Exception as e:
    print(f"[ERROR] Test failed: {e}")

# Test 6: Verify unit conversion
print("\n[TEST 6] Unit Conversion")
print("-"*80)

try:
    config_file = Path("config/scada_mapping.json")
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    pressure_unit = config.get('data_processing', {}).get('pressure_unit', 'unknown')
    print(f"Config pressure_unit: {pressure_unit}")
    
    # Check if có conversion code
    code_file = Path("services/scada_boundary_service.py")
    with open(code_file, 'r', encoding='utf-8') as f:
        code = f.read()
    
    conversion_keywords = ['convert', 'unit', 'bar', 'psi', 'kpa', 'm', 'meter']
    has_conversion = any(kw in code.lower() for kw in conversion_keywords)
    
    if has_conversion:
        print("[OK] Code co unit conversion logic")
    else:
        print("[ISSUE] Code khong co unit conversion")
        print("   Gia dinh: SCADA va EPANET cung unit")
        print("   Can: Verify SCADA API unit va convert neu can")
    
except Exception as e:
    print(f"[ERROR] Test failed: {e}")

print("\n" + "="*80)
print("DEEP AUDIT TEST COMPLETED")
print("="*80)
print("\nXem DEEP_AUDIT_CRITICAL_ISSUES.md de biet chi tiet cac van de")

