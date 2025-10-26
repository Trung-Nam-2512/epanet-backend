"""
Test to verify why Node 2 demand doesn't match inp file definition
"""
import wntr
from datetime import datetime

# Load network
wn = wntr.network.WaterNetworkModel('epanetVip1.inp')

# Get node 2
node2 = wn.get_node('2')

print("=" * 80)
print("NODE 2 CONFIGURATION FROM FILE:")
print("=" * 80)

# Check demand timeseries
if node2.demand_timeseries_list:
    for i, demand_ts in enumerate(node2.demand_timeseries_list):
        print(f"\nDemand timeseries #{i}:")
        print(f"  Base value: {demand_ts.base_value} m³/s")
        print(f"  Base value: {demand_ts.base_value * 1000} LPS")
        print(f"  Pattern name: {demand_ts.pattern_name}")
        if demand_ts.pattern_name:
            pattern = wn.get_pattern(demand_ts.pattern_name)
            print(f"  Pattern multipliers (first 6): {pattern.multipliers[:6]}")
else:
    print("No demand timeseries!")

# Get default pattern from options
print("\n" + "=" * 80)
print("GLOBAL PATTERN SETTINGS:")
print("=" * 80)
print(f"Default pattern ID: {wn.options.hydraulic.pattern}")

# Test simulation at hour 5
print("\n" + "=" * 80)
print("SIMULATION TEST AT HOUR 5:00:")
print("=" * 80)

wn.options.time.start_clocktime = 5 * 3600
wn.options.time.duration = 1 * 3600
wn.options.time.hydraulic_timestep = 3600
wn.options.time.report_timestep = 3600

sim = wntr.sim.WNTRSimulator(wn)
results = sim.run_sim()

timestamps = results.node['demand'].index
demand_t0 = results.node['demand'].loc[timestamps[0], '2']

print(f"\nTimestamp 0 (5:00 AM):")
print(f"  Expected (base_demand × pattern[5]): 0.04872 × 0.69 = {0.04872 * 0.69:.6f} LPS")
print(f"  Actual from simulation: {demand_t0 * 1000:.6f} LPS")
print(f"  Difference: {abs(0.04872 * 0.69 - demand_t0 * 1000):.6f} LPS")

# Check if pattern is being applied
if demand_t0 * 1000 < 0.04872 * 0.69:
    print(f"\n⚠️ WARNING: Actual demand is LOWER than expected!")
    print(f"  This suggests pattern may not be applied correctly")
    print(f"  OR base_demand in file is different from what we expect")

# Read inp file directly to verify
print("\n" + "=" * 80)
print("VERIFY FROM INP FILE DIRECTLY:")
print("=" * 80)
with open('epanetVip1.inp', 'r') as f:
    in_demands = False
    for line in f:
        if '[DEMANDS]' in line:
            in_demands = True
            continue
        if in_demands:
            if line.startswith('['):
                break
            if line.strip() and not line.strip().startswith(';'):
                parts = line.split()
                if parts and parts[0] == '2':
                    print(f"Node 2 in [DEMANDS] section: {line.strip()}")
                    if len(parts) >= 2:
                        print(f"  Junction ID: {parts[0]}")
                        print(f"  Base Demand: {parts[1]} LPS")
                        if len(parts) >= 3:
                            print(f"  Pattern: {parts[2]}")
                        else:
                            print(f"  Pattern: NOT SPECIFIED (will use default pattern '1')")

print("\n" + "=" * 80)
print("CONCLUSION:")
print("=" * 80)
print("If pattern is NOT specified in [DEMANDS], EPANET uses the default pattern")
print(f"Default pattern is: '{wn.options.hydraulic.pattern}'")

