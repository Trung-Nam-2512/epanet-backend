#!/usr/bin/env python3
"""
Phân tích tác động của việc xóa pattern và tìm giải pháp tốt hơn
"""

import wntr
import shutil
from datetime import datetime

def analyze_pattern_removal_impact():
    """Phân tích tác động của việc xóa pattern"""
    print("=" * 80)
    print("PHAN TICH TAC DONG CUA VIEC XOA PATTERN")
    print("=" * 80)
    
    # Load original file
    wn_original = wntr.network.WaterNetworkModel('epanet.inp')
    
    print("\n1. CURRENT STATE:")
    print("-" * 50)
    
    # Check current demand configuration
    nodes_with_pattern = 0
    nodes_without_pattern = 0
    total_demand = 0
    
    for node_name in wn_original.node_name_list:
        node = wn_original.get_node(node_name)
        if hasattr(node, 'demand_timeseries_list') and node.demand_timeseries_list:
            total_demand += node.demand_timeseries_list[0].base_value
            if node.demand_timeseries_list[0].pattern:
                nodes_with_pattern += 1
            else:
                nodes_without_pattern += 1
    
    print(f"Nodes with pattern: {nodes_with_pattern}")
    print(f"Nodes without pattern: {nodes_without_pattern}")
    print(f"Total base demand: {total_demand * 1000:.2f} LPS")
    print(f"Patterns in file: {len(wn_original.pattern_name_list)}")
    
    print("\n2. IMPACT ANALYSIS:")
    print("-" * 50)
    
    # Test current simulation
    wn_original.options.time.duration = 1 * 3600
    wn_original.options.time.hydraulic_timestep = 3600
    wn_original.options.time.report_timestep = 3600
    
    sim_original = wntr.sim.WNTRSimulator(wn_original)
    results_original = sim_original.run_sim()
    
    # Get results
    timestamps = results_original.node['demand'].index
    total_demand_current = results_original.node['demand'].loc[timestamps[0]].sum()
    
    print(f"Current simulation total demand: {total_demand_current * 1000:.2f} LPS")
    print(f"Base demand vs actual demand ratio: {total_demand_current / total_demand:.3f}")
    
    print("\n3. ALTERNATIVE SOLUTIONS:")
    print("-" * 50)
    
    print("Option 1: Remove pattern from .inp file")
    print("  - Pros: Simple, effective")
    print("  - Cons: Loses pattern data permanently")
    
    print("\nOption 2: Create pattern with all 1.0 multipliers")
    print("  - Pros: Keeps pattern structure, neutral effect")
    print("  - Cons: Still applies pattern logic")
    
    print("\nOption 3: Modify WNTR simulation options")
    print("  - Pros: Keeps original file intact")
    print("  - Cons: Complex, may not work")
    
    print("\nOption 4: Post-process simulation results")
    print("  - Pros: Keeps everything intact")
    print("  - Cons: Complex, may affect other calculations")
    
    return {
        'nodes_with_pattern': nodes_with_pattern,
        'nodes_without_pattern': nodes_without_pattern,
        'total_base_demand': total_demand,
        'total_actual_demand': total_demand_current,
        'ratio': total_demand_current / total_demand
    }

def test_pattern_modification():
    """Test việc modify pattern thay vì xóa"""
    print("\n4. TESTING PATTERN MODIFICATION:")
    print("-" * 50)
    
    # Load network
    wn = wntr.network.WaterNetworkModel('epanet.inp')
    
    # Create backup of original pattern
    original_pattern = wn.get_pattern('1')
    original_multipliers = original_pattern.multipliers.copy()
    
    print(f"Original pattern multipliers: {original_multipliers[:5]}...")
    
    # Test 1: Set all multipliers to 1.0
    wn.get_pattern('1').multipliers = [1.0] * 24
    print("Set all pattern multipliers to 1.0")
    
    # Test simulation
    wn.options.time.duration = 1 * 3600
    wn.options.time.hydraulic_timestep = 3600
    wn.options.time.report_timestep = 3600
    
    sim = wntr.sim.WNTRSimulator(wn)
    results = sim.run_sim()
    
    timestamps = results.node['demand'].index
    node2_demand_m3s = results.node['demand'].loc[timestamps[0], '2']
    node2_demand_lps = node2_demand_m3s * 1000
    
    print(f"Node 2 demand with 1.0 multipliers: {node2_demand_lps:.5f} LPS")
    
    # Restore original pattern
    wn.get_pattern('1').multipliers = original_multipliers
    
    return node2_demand_lps

def test_demand_multiplier_option():
    """Test sử dụng demand_multiplier option"""
    print("\n5. TESTING DEMAND_MULTIPLIER OPTION:")
    print("-" * 50)
    
    # Load network
    wn = wntr.network.WaterNetworkModel('epanet.inp')
    
    # Test with different demand_multiplier values
    multipliers_to_test = [1.0, 0.22, 0.68]
    
    for mult in multipliers_to_test:
        wn.options.hydraulic.demand_multiplier = mult
        
        sim = wntr.sim.WNTRSimulator(wn)
        results = sim.run_sim()
        
        timestamps = results.node['demand'].index
        node2_demand_m3s = results.node['demand'].loc[timestamps[0], '2']
        node2_demand_lps = node2_demand_m3s * 1000
        
        print(f"Demand multiplier {mult}: Node 2 demand = {node2_demand_lps:.5f} LPS")
    
    return True

def main():
    """Main function"""
    try:
        # Analyze impact
        impact = analyze_pattern_removal_impact()
        
        # Test pattern modification
        modified_demand = test_pattern_modification()
        
        # Test demand multiplier
        test_demand_multiplier_option()
        
        print("\n" + "=" * 80)
        print("RECOMMENDATIONS:")
        print("=" * 80)
        
        print("1. BEST OPTION: Modify pattern multipliers to 1.0")
        print("   - Keeps pattern structure intact")
        print("   - Neutral effect on demand")
        print("   - Easy to implement")
        
        print("\n2. ALTERNATIVE: Use demand_multiplier = 1.0")
        print("   - Global multiplier for all demands")
        print("   - May affect other calculations")
        
        print("\n3. LAST RESORT: Remove pattern from .inp")
        print("   - Simple but loses pattern data")
        print("   - May break other parts of system")
        
        print(f"\nCurrent ratio: {impact['ratio']:.3f}")
        print("Target ratio: 1.000 (no pattern effect)")
        
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    main()
