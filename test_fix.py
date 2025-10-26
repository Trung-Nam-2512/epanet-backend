"""
Test if pattern_start fix works
"""
import wntr

wn = wntr.network.WaterNetworkModel('epanetVip1.inp')

# Set both start_clocktime and pattern_start
wn.options.time.start_clocktime = 5 * 3600
wn.options.time.pattern_start = 5 * 3600  # FIX!
wn.options.time.duration = 1 * 3600
wn.options.time.hydraulic_timestep = 3600
wn.options.time.report_timestep = 3600

sim = wntr.sim.WNTRSimulator(wn)
results = sim.run_sim()

timestamps = results.node['demand'].index
demand_t0 = results.node['demand'].loc[timestamps[0], '2'] * 1000

node2 = wn.get_node('2')
base_demand = node2.demand_timeseries_list[0].base_value * 1000
pattern = wn.get_pattern('1')

expected = base_demand * pattern.multipliers[5]

print("=" * 60)
print("TEST WITH pattern_start FIX:")
print("=" * 60)
print(f"Start clocktime: 5:00 AM")
print(f"Pattern start:   5:00 AM")
print(f"\nBase demand:     {base_demand:.6f} LPS")
print(f"Pattern[5]:      {pattern.multipliers[5]:.2f}")
print(f"Expected demand: {expected:.6f} LPS")
print(f"Actual demand:   {demand_t0:.6f} LPS")
print(f"\nMatch: {'✅ YES' if abs(demand_t0 - expected) < 0.0001 else '❌ NO'}")

