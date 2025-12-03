#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug script để kiểm tra SCADA data có được apply đúng không
"""

import sys
import io
import wntr
from datetime import datetime
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent))

from services.scada_boundary_service import scada_boundary_service
from services.scada_service import scada_service
from core.config import settings

def debug_scada_application():
    """Debug SCADA application"""
    
    print("=" * 80)
    print("DEBUG SCADA APPLICATION")
    print("=" * 80)
    print()
    
    # Step 1: Load model
    print("Step 1: Load EPANET model")
    print("-" * 80)
    wn = wntr.network.WaterNetworkModel(settings.epanet_input_file)
    reservoir = wn.get_node("TXU2")
    initial_base_head = reservoir.base_head
    print(f"  Initial base_head from .inp: {initial_base_head:.2f}m")
    print()
    
    # Step 2: Get SCADA data
    print("Step 2: Get SCADA data")
    print("-" * 80)
    scada_result = scada_service.get_realtime_data_for_epanet(
        station_codes="13085",
        hours_back=1
    )
    
    if not scada_result["success"]:
        print(f"  ❌ Failed to get SCADA data: {scada_result.get('error', 'Unknown error')}")
        return
    
    scada_boundary_data = scada_result.get("boundary_conditions", {})
    print(f"  ✅ SCADA data retrieved")
    print(f"  Stations: {list(scada_boundary_data.keys())}")
    
    if "13085" in scada_boundary_data:
        records = scada_boundary_data["13085"]
        print(f"  Records for 13085: {len(records)}")
        if records:
            first_record = records[0]
            print(f"  First record:")
            print(f"    Timestamp: {first_record.get('timestamp', 'N/A')}")
            print(f"    Pressure: {first_record.get('pressure', 'N/A')}")
            print(f"    Flow: {first_record.get('flow', 'N/A')}")
    print()
    
    # Step 3: Apply SCADA boundary
    print("Step 3: Apply SCADA boundary")
    print("-" * 80)
    applied = scada_boundary_service.apply_scada_boundary_conditions(
        wn=wn,
        scada_boundary_data=scada_boundary_data,
        simulation_duration_hours=1,
        hydraulic_timestep_hours=1,
        simulation_start_time=datetime.now()
    )
    
    print(f"  Applied: {applied}")
    print(f"  Final base_head: {reservoir.base_head:.2f}m")
    print(f"  Pattern name: {reservoir.head_pattern_name}")
    
    if reservoir.head_pattern_name:
        pattern = wn.get_pattern(reservoir.head_pattern_name)
        print(f"  Pattern multipliers: {pattern.multipliers[:5]}... (first 5)")
        print(f"  Pattern length: {len(pattern.multipliers)}")
    
    print()
    
    # Step 4: Calculate expected head
    print("Step 4: Calculate expected head")
    print("-" * 80)
    from config.scada_mapping import load_scada_mapping
    mapping = load_scada_mapping()
    station_mapping = mapping.get("scada_stations", {}).get("13085", {})
    epanet_mapping = station_mapping.get("epanet_mapping", {})
    pressure_type = epanet_mapping.get("pressure_type", "absolute")
    
    print(f"  Config pressure_type: {pressure_type}")
    
    if "13085" in scada_boundary_data and scada_boundary_data["13085"]:
        scada_pressure = scada_boundary_data["13085"][0].get("pressure")
        if scada_pressure:
            if pressure_type == "gauge":
                expected_head = initial_base_head + scada_pressure
                print(f"  SCADA P1 (gauge): {scada_pressure:.2f}m")
                print(f"  Elevation (from .inp): {initial_base_head:.2f}m")
                print(f"  Expected Head: {expected_head:.2f}m = {initial_base_head:.2f}m + {scada_pressure:.2f}m")
            else:
                expected_head = scada_pressure
                print(f"  SCADA P1 (absolute): {scada_pressure:.2f}m")
                print(f"  Expected Head: {expected_head:.2f}m (direct)")
            
            actual_head = reservoir.base_head
            print(f"  Actual Head: {actual_head:.2f}m")
            
            if abs(actual_head - expected_head) < 0.1:
                print(f"  ✅ Head matches expected value!")
            else:
                print(f"  ❌ Head mismatch! Expected: {expected_head:.2f}m, Actual: {actual_head:.2f}m")
                print(f"  Difference: {abs(actual_head - expected_head):.2f}m")
    
    print()
    print("=" * 80)

if __name__ == "__main__":
    debug_scada_application()

