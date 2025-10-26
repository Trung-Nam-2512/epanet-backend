"""
Test to see if changing elevation affects demand calculation
"""
import wntr

# Load network
wn = wntr.network.WaterNetworkModel('epanetVip1.inp')

# Get node 2 original elevation
node2 = wn.get_node('2')
original_elevation = node2.elevation

print("=" * 80)
print("TEST 1: ORIGINAL CONFIGURATION")
print("=" * 80)
print(f"Node 2 original elevation: {original_elevation} m")

# Run simulation with original settings
wn.options.time.start_clocktime = 5 * 3600
wn.options.time.duration = 1 * 3600
wn.options.time.hydraulic_timestep = 3600
wn.options.time.report_timestep = 3600

sim = wntr.sim.WNTRSimulator(wn)
results = sim.run_sim()

timestamps = results.node['demand'].index
demand_original = results.node['demand'].loc[timestamps[0], '2']
pressure_original = results.node['pressure'].loc[timestamps[0], '2']
head_original = results.node['head'].loc[timestamps[0], '2']

print(f"Demand: {demand_original * 1000:.6f} LPS")
print(f"Pressure: {pressure_original:.6f} m")
print(f"Head: {head_original:.6f} m")

# Test 2: Change elevation like SCADA does
print("\n" + "=" * 80)
print("TEST 2: WITH SCADA ELEVATION UPDATE (like real simulation)")
print("=" * 80)

# Reload network
wn = wntr.network.WaterNetworkModel('epanetVip1.inp')
node2 = wn.get_node('2')

# Simulate SCADA update - set elevation to head value from SCADA
# From logs: "Updated elevation for node 2: 21.18 m"
scada_head = 21.18
node2.elevation = scada_head
print(f"Node 2 elevation changed to: {node2.elevation} m (from SCADA head)")

wn.options.time.start_clocktime = 5 * 3600
wn.options.time.duration = 1 * 3600
wn.options.time.hydraulic_timestep = 3600
wn.options.time.report_timestep = 3600

sim = wntr.sim.WNTRSimulator(wn)
results = sim.run_sim()

timestamps = results.node['demand'].index
demand_modified = results.node['demand'].loc[timestamps[0], '2']
pressure_modified = results.node['pressure'].loc[timestamps[0], '2']
head_modified = results.node['head'].loc[timestamps[0], '2']

print(f"Demand: {demand_modified * 1000:.6f} LPS")
print(f"Pressure: {pressure_modified:.6f} m")
print(f"Head: {head_modified:.6f} m")

# Compare
print("\n" + "=" * 80)
print("COMPARISON:")
print("=" * 80)
print(f"Original elevation: {original_elevation:.2f} m")
print(f"SCADA elevation:    {scada_head:.2f} m")
print(f"Elevation change:   {scada_head - original_elevation:.2f} m")
print()
print(f"Original demand:    {demand_original * 1000:.6f} LPS")
print(f"Modified demand:    {demand_modified * 1000:.6f} LPS")
print(f"Demand change:      {(demand_modified - demand_original) * 1000:.6f} LPS ({((demand_modified - demand_original) / demand_original * 100):.1f}%)")
print()
print(f"Original pressure:  {pressure_original:.6f} m")
print(f"Modified pressure:  {pressure_modified:.6f} m")
print(f"Pressure change:    {pressure_modified - pressure_original:.6f} m")

print("\n" + "=" * 80)
print("ANALYSIS:")
print("=" * 80)
if abs(demand_modified - demand_original) < 1e-8:
    print("✅ Elevation change does NOT affect demand calculation")
    print("   Demand is purely base_demand × pattern, independent of elevation")
else:
    print("⚠️ Elevation change DOES affect demand!")
    print("   This could be due to pressure-dependent demand or other factors")

print("\n" + "=" * 80)
print("PRESSURE-DEPENDENT DEMAND CHECK:")
print("=" * 80)

# Check if pressure-dependent demand is enabled
if hasattr(node2, 'minimum_pressure'):
    print(f"Minimum pressure: {node2.minimum_pressure}")
    print(f"Required pressure: {node2.nominal_pressure if hasattr(node2, 'nominal_pressure') else 'N/A'}")
    print("Note: WNTR may use pressure-dependent demand by default")
else:
    print("No pressure-dependent demand settings found")

# Check EPANET demand model option
print(f"\nDemand model in options: {wn.options.hydraulic.demand_model if hasattr(wn.options.hydraulic, 'demand_model') else 'Not set'}")

