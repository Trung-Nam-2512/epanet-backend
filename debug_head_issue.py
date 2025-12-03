#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug script để tìm nguyên nhân head cao
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from services.scada_boundary_service import SCADABoundaryService
import wntr

def debug_head_issue():
    """Debug head calculation issue"""
    
    print("=" * 80)
    print("DEBUG HEAD ISSUE")
    print("=" * 80)
    print()
    
    # Load WNTR model
    inp_file = "epanetVip1.inp"
    wn = wntr.network.WaterNetworkModel(inp_file)
    
    print("1. INITIAL STATE (from .inp file):")
    print("-" * 80)
    for reservoir_name in wn.reservoir_name_list:
        reservoir = wn.get_node(reservoir_name)
        print(f"Reservoir: {reservoir_name}")
        print(f"  base_head: {reservoir.base_head:.2f}m")
        print(f"  head_pattern_name: {reservoir.head_pattern_name}")
        if hasattr(reservoir, 'elevation'):
            print(f"  elevation: {reservoir.elevation:.2f}m")
        if hasattr(reservoir, 'head_timeseries'):
            test_head = reservoir.head_timeseries.at(0)
            print(f"  head_timeseries.at(0): {test_head:.2f}m")
        print()
    
    # Simulate SCADA data application
    print("2. SIMULATE SCADA DATA APPLICATION:")
    print("-" * 80)
    
    # SCADA data: P1 = 21.66m (gauge), elevation = 5.0m
    scada_pressure = 21.66  # gauge pressure
    elevation = 5.0  # from .inp
    expected_head = elevation + scada_pressure  # 5.0 + 21.66 = 26.66m
    
    print(f"SCADA P1 (gauge): {scada_pressure:.2f}m")
    print(f"Elevation (from .inp): {elevation:.2f}m")
    print(f"Expected head: {elevation:.2f}m + {scada_pressure:.2f}m = {expected_head:.2f}m")
    print()
    
    # Apply SCADA boundary
    scada_service = SCADABoundaryService()
    
    # Create mock SCADA data
    from datetime import datetime, timedelta
    now = datetime.now()
    scada_boundary_data = {
        "13085": [
            {
                "timestamp": (now - timedelta(hours=1)).isoformat(),
                "pressure": scada_pressure,
                "flow": 0.0
            },
            {
                "timestamp": now.isoformat(),
                "pressure": scada_pressure,
                "flow": 0.0
            }
        ]
    }
    
    # Apply SCADA boundary
    applied = scada_service.apply_scada_boundary_conditions(
        wn=wn,
        scada_boundary_data=scada_boundary_data,
        simulation_duration_hours=2,
        hydraulic_timestep_hours=1
    )
    
    print()
    print("3. AFTER SCADA APPLICATION:")
    print("-" * 80)
    for reservoir_name in wn.reservoir_name_list:
        reservoir = wn.get_node(reservoir_name)
        print(f"Reservoir: {reservoir_name}")
        print(f"  base_head: {reservoir.base_head:.2f}m")
        print(f"  head_pattern_name: {reservoir.head_pattern_name}")
        if hasattr(reservoir, 'elevation'):
            print(f"  elevation: {reservoir.elevation:.2f}m")
        if hasattr(reservoir, 'head_timeseries'):
            test_head = reservoir.head_timeseries.at(0)
            print(f"  head_timeseries.at(0): {test_head:.2f}m")
            if reservoir.head_pattern_name:
                pattern = wn.get_pattern(reservoir.head_pattern_name)
                print(f"  Pattern multipliers: {pattern.multipliers[:5]}... (first 5)")
                # Calculate expected head
                if len(pattern.multipliers) > 0:
                    calculated_head = reservoir.base_head * pattern.multipliers[0]
                    print(f"  Calculated head (base_head * multiplier[0]): {calculated_head:.2f}m")
        print()
    
    # Run simulation
    print("4. RUN SIMULATION:")
    print("-" * 80)
    wn.options.time.duration = 2 * 3600  # 2 hours
    wn.options.time.hydraulic_timestep = 3600  # 1 hour
    wn.options.time.report_timestep = 3600
    
    sim = wntr.sim.WNTRSimulator(wn)
    results = sim.run_sim()
    
    # Get reservoir head
    for reservoir_name in wn.reservoir_name_list:
        if reservoir_name in results.node['head'].columns:
            reservoir_heads = results.node['head'].loc[:, reservoir_name]
            print(f"Reservoir {reservoir_name} head in simulation:")
            for i, (time, head) in enumerate(reservoir_heads.items()):
                if i < 3:
                    print(f"  Time {time}s: {head:.2f}m")
            print()
            
            # Check if head matches expected
            first_head = reservoir_heads.iloc[0]
            if abs(first_head - expected_head) > 0.01:
                print(f"⚠️ PROBLEM: Expected head = {expected_head:.2f}m, but simulation head = {first_head:.2f}m")
                print(f"  Difference: {abs(first_head - expected_head):.2f}m")
                print()
                
                # Check if it's exactly double
                if abs(first_head - expected_head * 2) < 0.01:
                    print(f"  ⚠️ Head is exactly DOUBLE! ({first_head:.2f}m = {expected_head:.2f}m * 2)")
                    print(f"  Possible cause: Pattern multiplier is being applied twice?")
                elif abs(first_head - (expected_head + elevation)) < 0.01:
                    print(f"  ⚠️ Head = expected + elevation! ({first_head:.2f}m = {expected_head:.2f}m + {elevation:.2f}m)")
                    print(f"  Possible cause: Elevation is being added twice?")
    
    print("=" * 80)

if __name__ == "__main__":
    debug_head_issue()

