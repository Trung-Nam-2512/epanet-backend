#!/usr/bin/env python3
"""
Test script để verify logic demand cố định
"""

import wntr
from datetime import datetime

def test_fixed_demand_logic():
    """Test logic demand co dinh"""
    print("=" * 80)
    print("TEST LOGIC DEMAND CO DINH")
    print("=" * 80)
    
    # Load network
    wn = wntr.network.WaterNetworkModel('epanet.inp')
    
    print("\n1. DEMAND TRUOC KHI SUA:")
    print("-" * 50)
    
    # Get node 2 before modification
    node2_before = wn.get_node('2')
    base_demand_m3s = node2_before.demand_timeseries_list[0].base_value
    base_demand_lps = base_demand_m3s * 1000
    
    print(f"Node 2 base demand: {base_demand_lps:.5f} LPS")
    
    # Check if pattern is applied
    if node2_before.demand_timeseries_list[0].pattern:
        pattern_id = node2_before.demand_timeseries_list[0].pattern
        pattern = wn.get_pattern(pattern_id)
        current_hour = datetime.now().hour
        pattern_mult = pattern.multipliers[current_hour]
        expected_demand = base_demand_lps * pattern_mult
        print(f"Pattern {pattern_id} multiplier for hour {current_hour}: {pattern_mult:.2f}")
        print(f"Expected demand with pattern: {expected_demand:.5f} LPS")
    else:
        print("No pattern applied")
    
    print("\n2. AP DUNG LOGIC DEMAND CO DINH:")
    print("-" * 50)
    
    # Apply fixed demand logic
    for node_name in wn.node_name_list:
        node = wn.get_node(node_name)
        if hasattr(node, 'demand_timeseries_list') and node.demand_timeseries_list:
            # Set base demand to fixed value, remove pattern
            base_demand = node.demand_timeseries_list[0].base_value
            node.demand_timeseries_list.clear()
            # Add fixed demand without pattern
            node.demand_timeseries_list.append((base_demand, None))
    
    # Remove pattern from network completely
    wn.pattern_name_list.clear()
    print("Removed all patterns from network")
    
    print("\n3. DEMAND SAU KHI SUA:")
    print("-" * 50)
    
    # Check node 2 after modification
    node2_after = wn.get_node('2')
    fixed_demand_m3s = node2_after.demand_timeseries_list[0].base_value
    fixed_demand_lps = fixed_demand_m3s * 1000
    
    print(f"Node 2 fixed demand: {fixed_demand_lps:.5f} LPS")
    
    if node2_after.demand_timeseries_list[0].pattern:
        print(f"Pattern still applied: {node2_after.demand_timeseries_list[0].pattern}")
    else:
        print("No pattern applied - using fixed demand")
    
    print("\n4. SIMULATION TEST:")
    print("-" * 50)
    
    # Run simulation
    wn.options.time.duration = 1 * 3600
    wn.options.time.hydraulic_timestep = 3600
    wn.options.time.report_timestep = 3600
    wn.options.time.start_clocktime = 0
    wn.options.time.pattern_start = 0
    
    # Disable pattern application globally
    wn.options.hydraulic.demand_multiplier = 1.0
    
    sim = wntr.sim.WNTRSimulator(wn)
    results = sim.run_sim()
    
    timestamps = results.node['demand'].index
    actual_demand_m3s = results.node['demand'].loc[timestamps[0], '2']
    actual_demand_lps = actual_demand_m3s * 1000
    
    print(f"Simulation results:")
    print(f"  - Fixed demand: {fixed_demand_lps:.5f} LPS")
    print(f"  - Actual demand: {actual_demand_lps:.5f} LPS")
    print(f"  - Match: {'YES' if abs(fixed_demand_lps - actual_demand_lps) < 0.0001 else 'NO'}")
    
    print("\n5. PATTERN DATA (FOR DISPLAY):")
    print("-" * 50)
    
    # Get pattern data for display
    pattern = wn.get_pattern('1')
    print(f"Pattern 1 multipliers (24 hours):")
    for i, mult in enumerate(pattern.multipliers):
        print(f"  Hour {i:2d}: {mult:.2f}")
    
    print(f"\nNote: Pattern multipliers are for display only.")
    print(f"      Simulation uses fixed demand: {fixed_demand_lps:.5f} LPS")
    
    return {
        'base_demand_lps': base_demand_lps,
        'fixed_demand_lps': fixed_demand_lps,
        'actual_demand_lps': actual_demand_lps,
        'pattern_multipliers': pattern.multipliers.tolist()
    }

def main():
    """Main test function"""
    try:
        results = test_fixed_demand_logic()
        
        print("\n" + "=" * 80)
        print("SUMMARY:")
        print("=" * 80)
        print(f"Base demand: {results['base_demand_lps']:.5f} LPS")
        print(f"Fixed demand: {results['fixed_demand_lps']:.5f} LPS")
        print(f"Actual demand: {results['actual_demand_lps']:.5f} LPS")
        
        if abs(results['fixed_demand_lps'] - results['actual_demand_lps']) < 0.0001:
            print("SUCCESS: Fixed demand logic working correctly!")
        else:
            print("ERROR: Fixed demand logic not working")
            
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    main()
