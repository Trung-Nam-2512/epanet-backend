#!/usr/bin/env python3
"""
Kiểm tra WNTR pattern behavior
"""

import wntr
from datetime import datetime

def check_wntr_pattern_behavior():
    """Kiểm tra cách WNTR xử lý pattern"""
    print("=" * 80)
    print("KIEM TRA WNTR PATTERN BEHAVIOR")
    print("=" * 80)
    
    # Load network
    wn = wntr.network.WaterNetworkModel('epanet.inp')
    
    print("\n1. DEMAND CONFIGURATION:")
    print("-" * 50)
    
    # Check node 2
    node2 = wn.get_node('2')
    print(f"Node 2 demand timeseries list: {len(node2.demand_timeseries_list)}")
    
    for i, ts in enumerate(node2.demand_timeseries_list):
        print(f"  Timeseries {i}:")
        print(f"    - Base value: {ts.base_value:.6f} m³/s")
        print(f"    - Pattern: {ts.pattern}")
        print(f"    - Pattern type: {type(ts.pattern)}")
    
    print("\n2. PATTERN DETAILS:")
    print("-" * 50)
    
    # Check pattern 1
    if '1' in wn.pattern_name_list:
        pattern = wn.get_pattern('1')
        print(f"Pattern 1:")
        print(f"  - Multipliers: {pattern.multipliers}")
        print(f"  - Length: {len(pattern.multipliers)}")
        print(f"  - Type: {type(pattern.multipliers)}")
        
        # Check current hour
        current_hour = datetime.now().hour
        print(f"  - Current hour: {current_hour}")
        print(f"  - Multiplier for hour {current_hour}: {pattern.multipliers[current_hour]:.2f}")
    
    print("\n3. WNTR SIMULATION BEHAVIOR:")
    print("-" * 50)
    
    # Test simulation
    wn.options.time.duration = 1 * 3600
    wn.options.time.hydraulic_timestep = 3600
    wn.options.time.report_timestep = 3600
    wn.options.time.start_clocktime = 0
    wn.options.time.pattern_start = 0
    
    sim = wntr.sim.WNTRSimulator(wn)
    results = sim.run_sim()
    
    # Get demand results
    timestamps = results.node['demand'].index
    actual_demand_m3s = results.node['demand'].loc[timestamps[0], '2']
    actual_demand_lps = actual_demand_m3s * 1000
    
    base_demand_m3s = node2.demand_timeseries_list[0].base_value
    base_demand_lps = base_demand_m3s * 1000
    
    print(f"Base demand: {base_demand_lps:.5f} LPS")
    print(f"Actual demand: {actual_demand_lps:.5f} LPS")
    
    # Calculate ratio
    ratio = actual_demand_lps / base_demand_lps
    print(f"Ratio: {ratio:.3f}")
    
    # Check which pattern multiplier this matches
    pattern = wn.get_pattern('1')
    for i, mult in enumerate(pattern.multipliers):
        if abs(mult - ratio) < 0.01:
            print(f"Matches pattern hour {i}: {mult:.3f}")
            break
    
    print("\n4. WNTR INTERNAL LOGIC:")
    print("-" * 50)
    
    print("WNTR automatically applies pattern multipliers to demand.")
    print("Even if you set pattern=None, WNTR may use default pattern behavior.")
    print("This is why actual demand = base_demand × pattern_multiplier")
    
    print("\n5. TESTING PATTERN REMOVAL:")
    print("-" * 50)
    
    # Try to remove pattern completely
    node2.demand_timeseries_list.clear()
    node2.demand_timeseries_list.append((base_demand_m3s, None))
    
    print("Set pattern=None for node 2")
    
    # Test again
    sim2 = wntr.sim.WNTRSimulator(wn)
    results2 = sim2.run_sim()
    
    timestamps2 = results2.node['demand'].index
    actual_demand2_m3s = results2.node['demand'].loc[timestamps2[0], '2']
    actual_demand2_lps = actual_demand2_m3s * 1000
    
    print(f"After setting pattern=None:")
    print(f"  - Actual demand: {actual_demand2_lps:.5f} LPS")
    print(f"  - Ratio: {actual_demand2_lps/base_demand_lps:.3f}")
    
    if abs(actual_demand2_lps - base_demand_lps) < 0.0001:
        print("SUCCESS: Pattern removed!")
    else:
        print("FAILED: Pattern still applied")
    
    return {
        'base_demand_lps': base_demand_lps,
        'actual_demand_lps': actual_demand_lps,
        'actual_demand2_lps': actual_demand2_lps,
        'ratio': ratio
    }

def main():
    """Main function"""
    try:
        results = check_wntr_pattern_behavior()
        
        print("\n" + "=" * 80)
        print("CONCLUSION:")
        print("=" * 80)
        print("WNTR automatically applies pattern multipliers to demand.")
        print("To use fixed demand, we need to:")
        print("1. Remove pattern references from .inp file")
        print("2. Or modify WNTR simulation logic")
        print("3. Or accept pattern behavior and document it")
        
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    main()
