"""
Verify demand calculation: why 0.010718 instead of 0.033617?
"""
import wntr

# Load network
wn = wntr.network.WaterNetworkModel('epanetVip1.inp')

# Get node 2 and pattern
node2 = wn.get_node('2')
pattern = wn.get_pattern('1')

print("=" * 80)
print("DEMAND CALCULATION VERIFICATION")
print("=" * 80)

# Get base demand
base_demand_m3s = node2.demand_timeseries_list[0].base_value
base_demand_lps = base_demand_m3s * 1000

print(f"\nBase demand from file:")
print(f"  Value in m³/s: {base_demand_m3s}")
print(f"  Value in LPS:  {base_demand_lps}")
print(f"  Expected:      0.04872 LPS")

# Get pattern multiplier at hour 5
pattern_mult_5 = pattern.multipliers[5]
print(f"\nPattern multiplier at hour 5:")
print(f"  Value: {pattern_mult_5}")
print(f"  Expected: 0.69")

# Calculate expected demand
expected_demand_lps = base_demand_lps * pattern_mult_5
print(f"\nExpected demand at hour 5:")
print(f"  Calculation: {base_demand_lps} × {pattern_mult_5} = {expected_demand_lps} LPS")

# Run simulation and get actual demand
wn.options.time.start_clocktime = 5 * 3600
wn.options.time.duration = 1 * 3600
wn.options.time.hydraulic_timestep = 3600
wn.options.time.report_timestep = 3600

sim = wntr.sim.WNTRSimulator(wn)
results = sim.run_sim()

timestamps = results.node['demand'].index
actual_demand_m3s = results.node['demand'].loc[timestamps[0], '2']
actual_demand_lps = actual_demand_m3s * 1000

print(f"\nActual demand from simulation:")
print(f"  Value in m³/s: {actual_demand_m3s}")
print(f"  Value in LPS:  {actual_demand_lps}")

# Calculate ratio
ratio = actual_demand_lps / expected_demand_lps if expected_demand_lps > 0 else 0

print(f"\n" + "=" * 80)
print("ANALYSIS:")
print("=" * 80)
print(f"Expected demand: {expected_demand_lps:.6f} LPS")
print(f"Actual demand:   {actual_demand_lps:.6f} LPS")
print(f"Ratio:           {ratio:.6f}")
print(f"Difference:      {abs(expected_demand_lps - actual_demand_lps):.6f} LPS")

# Check if ratio matches any pattern multiplier
print(f"\n" + "=" * 80)
print("PATTERN MULTIPLIER CHECK:")
print("=" * 80)
print(f"Ratio of actual/base: {actual_demand_lps / base_demand_lps:.6f}")
print(f"Pattern[5] expected:  {pattern_mult_5:.6f}")

# Check which pattern multiplier gives actual demand
for hour in range(24):
    calc_demand = base_demand_lps * pattern.multipliers[hour]
    if abs(calc_demand - actual_demand_lps) < 0.0001:
        print(f"\n✓ Actual demand matches pattern[{hour}] = {pattern.multipliers[hour]:.2f}")
        print(f"  This means simulation is using HOUR {hour}, not HOUR 5!")
        break
else:
    print(f"\n✗ Actual demand doesn't match ANY pattern multiplier")
    print(f"  This suggests something else is modifying demand")

# Test without start_clocktime
print(f"\n" + "=" * 80)
print("TEST: Simulation starting at hour 0 (midnight):")
print("=" * 80)

wn2 = wntr.network.WaterNetworkModel('epanetVip1.inp')
wn2.options.time.start_clocktime = 0  # Midnight
wn2.options.time.duration = 6 * 3600  # 6 hours
wn2.options.time.hydraulic_timestep = 3600
wn2.options.time.report_timestep = 3600

sim2 = wntr.sim.WNTRSimulator(wn2)
results2 = sim2.run_sim()

print("\nDemand at each hour starting from midnight:")
for i, ts in enumerate(results2.node['demand'].index[:6]):
    demand_lps = results2.node['demand'].loc[ts, '2'] * 1000
    expected = base_demand_lps * pattern.multipliers[i]
    print(f"  Hour {i}: {demand_lps:.6f} LPS (expected: {expected:.6f}, pattern: {pattern.multipliers[i]:.2f})")

