#!/usr/bin/env python3
"""
Tạo file .inp mới không có pattern để test demand cố định
"""

import wntr
import shutil

def create_fixed_demand_inp():
    """Tạo file .inp với demand cố định"""
    print("=" * 80)
    print("TAO FILE .INP VOI DEMAND CO DINH")
    print("=" * 80)
    
    # Load original file
    wn = wntr.network.WaterNetworkModel('epanet.inp')
    
    print("\n1. ORIGINAL FILE:")
    print("-" * 50)
    print(f"Patterns: {len(wn.pattern_name_list)}")
    print(f"Nodes: {len(wn.node_name_list)}")
    
    # Get node 2 demand
    node2 = wn.get_node('2')
    base_demand_m3s = node2.demand_timeseries_list[0].base_value
    base_demand_lps = base_demand_m3s * 1000
    print(f"Node 2 base demand: {base_demand_lps:.5f} LPS")
    
    print("\n2. CREATING FIXED DEMAND FILE:")
    print("-" * 50)
    
    # Remove all patterns
    wn.pattern_name_list.clear()
    
    # Set all nodes to fixed demand
    for node_name in wn.node_name_list:
        node = wn.get_node(node_name)
        if hasattr(node, 'demand_timeseries_list') and node.demand_timeseries_list:
            base_demand = node.demand_timeseries_list[0].base_value
            node.demand_timeseries_list.clear()
            node.demand_timeseries_list.append((base_demand, None))
    
    print("Applied fixed demand to all nodes")
    print("Removed all patterns")
    
    print("\n3. SAVING NEW FILE:")
    print("-" * 50)
    
    # Save new file
    new_file = 'epanet_fixed_demand.inp'
    wn.write_inpfile(new_file)
    print(f"Saved new file: {new_file}")
    
    print("\n4. TESTING NEW FILE:")
    print("-" * 50)
    
    # Load and test new file
    wn_new = wntr.network.WaterNetworkModel(new_file)
    
    print(f"New file patterns: {len(wn_new.pattern_name_list)}")
    print(f"New file nodes: {len(wn_new.node_name_list)}")
    
    # Test node 2
    node2_new = wn_new.get_node('2')
    new_demand_m3s = node2_new.demand_timeseries_list[0].base_value
    new_demand_lps = new_demand_m3s * 1000
    print(f"Node 2 new demand: {new_demand_lps:.5f} LPS")
    
    if node2_new.demand_timeseries_list[0].pattern:
        print(f"Pattern still applied: {node2_new.demand_timeseries_list[0].pattern}")
    else:
        print("No pattern applied - SUCCESS!")
    
    print("\n5. SIMULATION TEST:")
    print("-" * 50)
    
    # Run simulation
    wn_new.options.time.duration = 1 * 3600
    wn_new.options.time.hydraulic_timestep = 3600
    wn_new.options.time.report_timestep = 3600
    wn_new.options.time.start_clocktime = 0
    wn_new.options.time.pattern_start = 0
    
    sim = wntr.sim.WNTRSimulator(wn_new)
    results = sim.run_sim()
    
    timestamps = results.node['demand'].index
    actual_demand_m3s = results.node['demand'].loc[timestamps[0], '2']
    actual_demand_lps = actual_demand_m3s * 1000
    
    print(f"Simulation results:")
    print(f"  - Expected: {new_demand_lps:.5f} LPS")
    print(f"  - Actual:   {actual_demand_lps:.5f} LPS")
    print(f"  - Match:    {'YES' if abs(new_demand_lps - actual_demand_lps) < 0.0001 else 'NO'}")
    
    return {
        'original_demand_lps': base_demand_lps,
        'new_demand_lps': new_demand_lps,
        'actual_demand_lps': actual_demand_lps,
        'file_created': new_file
    }

def main():
    """Main function"""
    try:
        results = create_fixed_demand_inp()
        
        print("\n" + "=" * 80)
        print("SUMMARY:")
        print("=" * 80)
        print(f"Original demand: {results['original_demand_lps']:.5f} LPS")
        print(f"New demand: {results['new_demand_lps']:.5f} LPS")
        print(f"Actual demand: {results['actual_demand_lps']:.5f} LPS")
        print(f"File created: {results['file_created']}")
        
        if abs(results['new_demand_lps'] - results['actual_demand_lps']) < 0.0001:
            print("SUCCESS: Fixed demand working!")
        else:
            print("ERROR: Fixed demand not working")
            
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    main()
