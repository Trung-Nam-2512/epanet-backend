#!/usr/bin/env python3
"""
Báo cáo về logic Demand và Pattern trong Backend
"""

import wntr
from datetime import datetime

def analyze_demand_pattern_logic():
    """Phân tích logic demand và pattern"""
    print("=" * 80)
    print("BÁO CÁO LOGIC DEMAND VÀ PATTERN TRONG BACKEND")
    print("=" * 80)
    
    # Load network
    wn = wntr.network.WaterNetworkModel('epanet.inp')
    
    print("\n1. DEMAND CONFIGURATION:")
    print("-" * 50)
    
    # Get node 2 (main station)
    node2 = wn.get_node('2')
    base_demand_m3s = node2.demand_timeseries_list[0].base_value
    base_demand_lps = base_demand_m3s * 1000
    
    print(f"Node 2 base demand:")
    print(f"  - File value: {base_demand_lps:.5f} LPS")
    print(f"  - Unit: LPS (Liters per second)")
    
    # Get pattern
    pattern = wn.get_pattern('1')
    print(f"\nPattern 1 multipliers (24 hours):")
    for i, mult in enumerate(pattern.multipliers):
        print(f"  Hour {i:2d}: {mult:.2f}")
    
    print("\n2. CURRENT BACKEND LOGIC:")
    print("-" * 50)
    
    print("SCADA Service (_calculate_demand):")
    print("  - Returns None")
    print("  - Comment: 'Demand da co san trong file .inp, khong can tinh tu SCADA'")
    print("  - Comment: 'Chi can lay tu file .inp cho nut tuong ung'")
    
    print("\nEPANET Service (_update_wntr_real_time_data):")
    print("  - Comment: 'KHONG cap nhat demand tu SCADA - SU DUNG PATTERN DEMAND'")
    print("  - Comment: 'Chi cap nhat pressure va elevation tu SCADA'")
    print("  - Only updates: elevation, initial_level")
    print("  - Logs SCADA flow but doesn't use it")
    
    print("\n3. PATTERN APPLICATION:")
    print("-" * 50)
    
    # Test current hour
    current_hour = datetime.now().hour
    print(f"Current hour: {current_hour}")
    print(f"Pattern multiplier for hour {current_hour}: {pattern.multipliers[current_hour]:.2f}")
    
    # Calculate expected demand
    expected_demand_lps = base_demand_lps * pattern.multipliers[current_hour]
    print(f"Expected demand for hour {current_hour}: {expected_demand_lps:.5f} LPS")
    
    print("\n4. SIMULATION TEST:")
    print("-" * 50)
    
    # Run simulation at current hour
    wn.options.time.start_clocktime = current_hour * 3600
    wn.options.time.duration = 1 * 3600
    wn.options.time.hydraulic_timestep = 3600
    wn.options.time.report_timestep = 3600
    
    sim = wntr.sim.WNTRSimulator(wn)
    results = sim.run_sim()
    
    timestamps = results.node['demand'].index
    actual_demand_m3s = results.node['demand'].loc[timestamps[0], '2']
    actual_demand_lps = actual_demand_m3s * 1000
    
    print(f"Simulation results:")
    print(f"  - Expected: {expected_demand_lps:.5f} LPS")
    print(f"  - Actual:   {actual_demand_lps:.5f} LPS")
    print(f"  - Ratio:    {actual_demand_lps/expected_demand_lps:.3f}")
    
    print("\n5. ISSUE ANALYSIS:")
    print("-" * 50)
    
    # Check if actual matches any pattern multiplier
    ratio = actual_demand_lps / base_demand_lps
    print(f"Actual demand ratio to base: {ratio:.3f}")
    
    # Find closest pattern multiplier
    closest_mult = min(pattern.multipliers, key=lambda x: abs(x - ratio))
    closest_hour = list(pattern.multipliers).index(closest_mult)
    
    print(f"Closest pattern multiplier: {closest_mult:.3f} (hour {closest_hour})")
    print(f"Difference: {abs(ratio - closest_mult):.3f}")
    
    if abs(ratio - closest_mult) < 0.01:
        print("SUCCESS: Actual demand matches pattern multiplier")
    else:
        print("ISSUE: Actual demand doesn't match expected pattern")
    
    print("\n6. BACKEND CONFIGURATION:")
    print("-" * 50)
    
    print("Time settings in EPANET Service:")
    print(f"  - start_clocktime: {current_hour * 3600} seconds")
    print(f"  - pattern_start: {current_hour * 3600} seconds")
    print(f"  - duration: {24 * 3600} seconds")
    print(f"  - hydraulic_timestep: {1 * 3600} seconds")
    print(f"  - report_timestep: {1 * 3600} seconds")
    
    print("\n7. RECOMMENDATIONS:")
    print("-" * 50)
    
    print("Current approach:")
    print("  - Uses pattern-based demand (from .inp file)")
    print("  - Ignores SCADA flow data for demand calculation")
    print("  - Only uses SCADA for pressure/elevation updates")
    
    print("\nAlternative approaches:")
    print("  - Use SCADA flow data to override pattern demand")
    print("  - Blend pattern demand with SCADA flow data")
    print("  - Use SCADA flow as demand multiplier")
    
    return {
        'base_demand_lps': base_demand_lps,
        'current_hour': current_hour,
        'pattern_multiplier': pattern.multipliers[current_hour],
        'expected_demand_lps': expected_demand_lps,
        'actual_demand_lps': actual_demand_lps,
        'ratio': ratio,
        'closest_mult': closest_mult,
        'closest_hour': closest_hour
    }

def main():
    """Main analysis function"""
    try:
        results = analyze_demand_pattern_logic()
        
        print("\n" + "=" * 80)
        print("SUMMARY:")
        print("=" * 80)
        print(f"Base demand: {results['base_demand_lps']:.5f} LPS")
        print(f"Current hour: {results['current_hour']}")
        print(f"Pattern multiplier: {results['pattern_multiplier']:.2f}")
        print(f"Expected demand: {results['expected_demand_lps']:.5f} LPS")
        print(f"Actual demand: {results['actual_demand_lps']:.5f} LPS")
        print(f"Ratio: {results['ratio']:.3f}")
        
        if abs(results['ratio'] - results['closest_mult']) < 0.01:
            print("STATUS: Pattern working correctly")
        else:
            print("STATUS: Pattern not working as expected")
            
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    main()
