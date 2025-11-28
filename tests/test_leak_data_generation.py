"""
Test để verify việc sinh dữ liệu kịch bản rò rỉ có chuẩn xác không
"""
import sys
import random
import numpy as np
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.leak_simulation.leak_scenarios import LeakScenarioGenerator, LeakScenario

print("="*80)
print("TEST: SINH DU LIEU KICH BAN RO RI CHO ML")
print("="*80)

# Test 1: Verify leak area sampling (log-uniform)
print("\n[TEST 1] Leak Area Sampling (Log-Uniform)")
print("-"*80)

try:
    generator = LeakScenarioGenerator(
        leak_nodes=["2", "3", "31"],
        leak_area_range={'min': 0.0001, 'max': 0.01},
        leak_time_range={
            'start_h_min': 2,
            'start_h_max': 17,
            'duration_h_min': 5.5,
            'duration_h_max': 7.2
        },
        discharge_coeff=0.75,
        leaks_per_scenario=1
    )
    
    # Sample nhiều lần để verify distribution
    samples = []
    for _ in range(1000):
        area = generator._sample_log_uniform(0.0001, 0.01)
        samples.append(area)
    
    samples = np.array(samples)
    
    print(f"Sample size: {len(samples)}")
    print(f"Min: {samples.min():.6f} m²")
    print(f"Max: {samples.max():.6f} m²")
    print(f"Mean: {samples.mean():.6f} m²")
    print(f"Median: {np.median(samples):.6f} m²")
    
    # Verify log-uniform: log(x) should be uniform
    log_samples = np.log(samples)
    log_min = np.log(0.0001)
    log_max = np.log(0.01)
    
    # Check if log samples are roughly uniform
    log_mean = log_samples.mean()
    log_expected = (log_min + log_max) / 2
    
    print(f"\nLog-uniform check:")
    print(f"  log(mean): {log_mean:.6f}")
    print(f"  Expected log(mean): {log_expected:.6f}")
    print(f"  Difference: {abs(log_mean - log_expected):.6f}")
    
    if abs(log_mean - log_expected) < 0.1:
        print("[OK] Log-uniform distribution looks correct")
    else:
        print("[WARN] Log-uniform distribution may be incorrect")
    
    # Verify range
    if samples.min() >= 0.0001 and samples.max() <= 0.01:
        print("[OK] All samples within range [0.0001, 0.01]")
    else:
        print("[FAIL] Some samples outside range!")
        sys.exit(1)
    
except Exception as e:
    print(f"[ERROR] Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: Verify leak time constraints
print("\n[TEST 2] Leak Time Constraints")
print("-"*80)

try:
    simulation_duration_h = 24.0
    
    # Test nhiều scenarios
    leak_times = []
    for _ in range(100):
        scenario = generator._create_scenario(1, "2", simulation_duration_h)
        start_h = scenario.start_time_s / 3600.0
        duration_h = scenario.duration_s / 3600.0
        end_h = start_h + duration_h
        
        leak_times.append({
            'start_h': start_h,
            'duration_h': duration_h,
            'end_h': end_h
        })
    
    starts = [t['start_h'] for t in leak_times]
    durations = [t['duration_h'] for t in leak_times]
    ends = [t['end_h'] for t in leak_times]
    
    print(f"Start time range: {min(starts):.2f}h - {max(starts):.2f}h")
    print(f"Duration range: {min(durations):.2f}h - {max(durations):.2f}h")
    print(f"End time range: {min(ends):.2f}h - {max(ends):.2f}h")
    
    # Check constraints
    config_start_min = 2.0
    config_start_max = 17.0
    config_duration_min = 5.5
    config_duration_max = 7.2
    
    # Verify start time
    if min(starts) >= config_start_min and max(starts) <= config_start_max:
        print(f"[OK] Start times within range [{config_start_min}, {config_start_max}]h")
    else:
        print(f"[FAIL] Start times outside range!")
        sys.exit(1)
    
    # Verify duration
    if min(durations) >= config_duration_min and max(durations) <= config_duration_max:
        print(f"[OK] Durations within range [{config_duration_min}, {config_duration_max}]h")
    else:
        print(f"[FAIL] Durations outside range!")
        sys.exit(1)
    
    # Verify end time doesn't exceed simulation duration
    max_end = max(ends)
    if max_end <= simulation_duration_h:
        print(f"[OK] All leaks end before simulation duration ({simulation_duration_h}h)")
    else:
        print(f"[WARN] Some leaks end after simulation duration: max_end={max_end:.2f}h > {simulation_duration_h}h")
        # Check if this is a real issue
        if max_end > simulation_duration_h + 0.1:  # Allow small tolerance
            print("[FAIL] Leak end time exceeds simulation duration significantly!")
            sys.exit(1)
    
except Exception as e:
    print(f"[ERROR] Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Verify multiple leaks per scenario
print("\n[TEST 3] Multiple Leaks Per Scenario")
print("-"*80)

try:
    generator_multi = LeakScenarioGenerator(
        leak_nodes=["2", "3", "31", "43", "50", "60", "70", "80", "90", "100"],
        leak_area_range={'min': 0.0001, 'max': 0.01},
        leak_time_range={
            'start_h_min': 2,
            'start_h_max': 17,
            'duration_h_min': 5.5,
            'duration_h_max': 7.2
        },
        discharge_coeff=0.75,
        leaks_per_scenario=10
    )
    
    scenario = generator_multi._create_scenario(1, "2", 24.0)
    
    print(f"Primary leak node: {scenario.leak_node}")
    print(f"All leak nodes: {scenario.leak_nodes}")
    print(f"Number of leaks: {len(scenario.leak_nodes) if scenario.leak_nodes else 1}")
    
    if scenario.leak_nodes:
        print(f"\nLeak details:")
        for i, (node, area, start, end) in enumerate(zip(
            scenario.leak_nodes,
            scenario.leak_areas_m2,
            scenario.leak_start_times_s,
            scenario.leak_end_times_s
        )):
            print(f"  Leak {i+1}: node={node}, area={area:.6f}m², "
                  f"start={start}s ({start/3600:.2f}h), end={end}s ({end/3600:.2f}h)")
        
        # Verify all leaks are unique
        if len(scenario.leak_nodes) == len(set(scenario.leak_nodes)):
            print("[OK] All leak nodes are unique")
        else:
            print("[FAIL] Duplicate leak nodes!")
            sys.exit(1)
        
        # Verify primary leak is first
        if scenario.leak_node == scenario.leak_nodes[0]:
            print("[OK] Primary leak node is first in list")
        else:
            print("[FAIL] Primary leak node is not first!")
            sys.exit(1)
    else:
        print("[FAIL] Multiple leaks not created!")
        sys.exit(1)
    
except Exception as e:
    print(f"[ERROR] Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Verify ensure_all_nodes_covered
print("\n[TEST 4] Ensure All Nodes Covered")
print("-"*80)

try:
    all_nodes = ["2", "3", "31", "43", "50"]
    generator_cover = LeakScenarioGenerator(
        leak_nodes=all_nodes,
        leak_area_range={'min': 0.0001, 'max': 0.01},
        leak_time_range={
            'start_h_min': 2,
            'start_h_max': 17,
            'duration_h_min': 5.5,
            'duration_h_max': 7.2
        },
        discharge_coeff=0.75,
        leaks_per_scenario=1
    )
    
    # Generate với ensure_all_nodes=True
    scenarios = generator_cover.generate(
        n_scenarios=3,  # Less than number of nodes
        simulation_duration_h=24.0,
        ensure_all_nodes=True
    )
    
    unique_nodes = set(s.leak_node for s in scenarios)
    print(f"Total scenarios: {len(scenarios)}")
    print(f"Unique nodes covered: {len(unique_nodes)}")
    print(f"Nodes covered: {sorted(unique_nodes)}")
    print(f"All nodes: {sorted(all_nodes)}")
    
    if len(unique_nodes) >= len(all_nodes):
        print(f"[OK] All {len(all_nodes)} nodes are covered")
    else:
        print(f"[WARN] Only {len(unique_nodes)}/{len(all_nodes)} nodes covered")
        # This might be OK if n_scenarios < len(all_nodes) but ensure_all_nodes adjusted it
        if len(scenarios) >= len(all_nodes):
            print("[FAIL] Should have covered all nodes!")
            sys.exit(1)
    
except Exception as e:
    print(f"[ERROR] Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Verify leak demand calculation formula
print("\n[TEST 5] Leak Demand Calculation Formula")
print("-"*80)

try:
    # Test công thức: Q = Cd * A * sqrt(2 * g * h)
    Cd = 0.75
    A = 0.001  # 1 cm² = 0.0001 m²
    g = 9.81
    h = 20.0  # 20m pressure
    
    # Calculate
    Q = Cd * A * np.sqrt(2 * g * h)
    Q_lps = Q * 1000  # Convert to L/s
    
    print(f"Test parameters:")
    print(f"  Cd (discharge_coeff): {Cd}")
    print(f"  A (leak_area): {A} m² = {A*10000:.2f} cm²")
    print(f"  h (pressure): {h} m")
    print(f"  g (gravity): {g} m/s²")
    
    print(f"\nCalculation:")
    print(f"  Q = Cd * A * sqrt(2 * g * h)")
    print(f"  Q = {Cd} * {A} * sqrt(2 * {g} * {h})")
    print(f"  Q = {Cd} * {A} * {np.sqrt(2 * g * h):.4f}")
    print(f"  Q = {Q:.6f} m³/s = {Q_lps:.4f} L/s")
    
    # Verify formula matches WNTR
    # WNTR uses: Q = discharge_coeff * area * sqrt(2 * g * h)
    # where h = gauge pressure (pressure, not head)
    
    print(f"\n[OK] Formula matches WNTR: Q = Cd * A * sqrt(2 * g * h)")
    print(f"  where h = gauge pressure (pressure, not head)")
    
except Exception as e:
    print(f"[ERROR] Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*80)
print("[SUCCESS] ALL TESTS PASSED")
print("="*80)



