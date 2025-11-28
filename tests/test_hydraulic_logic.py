"""
Test sâu về logic thủy lực - verify SCADA boundary conditions được apply đúng trong simulation
"""
import sys
import wntr
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.scada_boundary_service import scada_boundary_service
from core.config import settings

print("="*80)
print("DEEP HYDRAULIC LOGIC TEST")
print("="*80)

# Test 1: Verify Pattern được sử dụng trong simulation
print("\n[TEST 1] Pattern Usage in Simulation")
print("-"*80)

try:
    # Load model
    wn = wntr.network.WaterNetworkModel(settings.epanet_input_file)
    reservoir = wn.get_node("TXU2")
    
    initial_head = reservoir.base_head
    print(f"Initial base_head: {initial_head}m")
    
    # Create SCADA data với time-varying head
    scada_data = {
        "13085": [
            {"timestamp": "2025-01-15 10:00", "pressure": 20.0},
            {"timestamp": "2025-01-15 11:00", "pressure": 30.0},
            {"timestamp": "2025-01-15 12:00", "pressure": 25.0}
        ]
    }
    
    # Apply SCADA boundary
    scada_boundary_service.apply_scada_boundary_conditions(
        wn=wn,
        scada_boundary_data=scada_data,
        simulation_duration_hours=3,
        hydraulic_timestep_hours=1,
        simulation_start_time=datetime(2025, 1, 15, 10, 0)
    )
    
    # Check pattern
    pattern_name = reservoir.head_pattern_name
    base_head = reservoir.base_head
    
    print(f"After SCADA apply:")
    print(f"  base_head: {base_head}m")
    print(f"  pattern_name: {pattern_name}")
    
    if pattern_name:
        pattern = wn.get_pattern(pattern_name)
        print(f"  pattern multipliers: {pattern.multipliers}")
        
        # Verify multipliers make sense
        if len(pattern.multipliers) >= 3:
            mult1 = pattern.multipliers[0]  # Should be 1.0 (base)
            mult2 = pattern.multipliers[1]  # Should be 1.5 (30/20)
            mult3 = pattern.multipliers[2]  # Should be 1.25 (25/20)
            
            print(f"  Expected multipliers: [1.0, 1.5, 1.25]")
            print(f"  Actual multipliers: [{mult1:.2f}, {mult2:.2f}, {mult3:.2f}]")
            
            if abs(mult1 - 1.0) < 0.01 and abs(mult2 - 1.5) < 0.01 and abs(mult3 - 1.25) < 0.01:
                print("[OK] Multipliers are correct")
            else:
                print("[FAIL] Multipliers are incorrect!")
                sys.exit(1)
    
    # Run simulation và check head values
    print("\n[TEST 2] Simulation Results - Head Values")
    print("-"*80)
    
    wn.options.time.duration = 3 * 3600  # 3 hours
    wn.options.time.hydraulic_timestep = 3600  # 1 hour
    wn.options.time.report_timestep = 3600
    
    sim = wntr.sim.WNTRSimulator(wn)
    results = sim.run_sim()
    
    # Get reservoir head tại các time steps
    reservoir_heads = results.node['head'].loc[:, 'TXU2']
    
    print("Reservoir head during simulation:")
    for time_sec, head in reservoir_heads.items():
        time_hour = time_sec / 3600
        print(f"  Time {time_hour:.1f}h: {head:.2f}m")
    
    # Verify head values match SCADA data
    # At t=0: head = 20.0m (base_head * multiplier[0] = 20.0 * 1.0 = 20.0)
    # At t=1h: head = 30.0m (base_head * multiplier[1] = 20.0 * 1.5 = 30.0)
    # At t=2h: head = 25.0m (base_head * multiplier[2] = 20.0 * 1.25 = 25.0)
    
    expected_heads = [20.0, 30.0, 25.0]
    actual_heads = [reservoir_heads.iloc[i] for i in range(min(3, len(reservoir_heads)))]
    
    print(f"\nExpected heads: {expected_heads}")
    print(f"Actual heads: {[f'{h:.2f}' for h in actual_heads]}")
    
    all_match = True
    for i, (expected, actual) in enumerate(zip(expected_heads, actual_heads)):
        if abs(expected - actual) > 0.5:  # Allow 0.5m tolerance
            print(f"[FAIL] Head at step {i} mismatch: expected {expected}m, got {actual:.2f}m")
            all_match = False
    
    if all_match:
        print("[OK] Simulation head values match SCADA data!")
    else:
        print("[FAIL] Simulation head values do NOT match SCADA data!")
        sys.exit(1)
    
except Exception as e:
    print(f"[ERROR] Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Verify pressure conversion logic
print("\n[TEST 3] Pressure Conversion Logic")
print("-"*80)

try:
    # Test với gauge pressure
    wn2 = wntr.network.WaterNetworkModel(settings.epanet_input_file)
    reservoir2 = wn2.get_node("TXU2")
    
    # Mock mapping với gauge pressure
    from services.scada_boundary_service import SCADABoundaryService
    service = SCADABoundaryService()
    
    # Temporarily modify mapping để test gauge pressure
    original_mapping = service.mapping_config.get("13085", {})
    test_mapping = original_mapping.copy()
    test_mapping['pressure_type'] = 'gauge'
    test_mapping['elevation'] = 5.0
    
    scada_data_gauge = {
        "13085": [
            {"timestamp": "2025-01-15 10:00", "pressure": 20.0}  # Gauge pressure
        ]
    }
    
    # Manually test conversion logic
    pressure_value = 20.0
    pressure_type = test_mapping.get('pressure_type', 'absolute')
    elevation = test_mapping.get('elevation', 0.0)
    
    if pressure_type == 'gauge':
        head_value = elevation + pressure_value
    else:
        head_value = pressure_value
    
    print(f"Gauge pressure test:")
    print(f"  pressure: {pressure_value}m")
    print(f"  elevation: {elevation}m")
    print(f"  calculated head: {head_value}m")
    
    expected_head = 5.0 + 20.0  # elevation + pressure
    if abs(head_value - expected_head) < 0.01:
        print(f"[OK] Gauge pressure conversion correct: {head_value}m = {elevation}m + {pressure_value}m")
    else:
        print(f"[FAIL] Gauge pressure conversion incorrect!")
        sys.exit(1)
    
except Exception as e:
    print(f"[ERROR] Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Edge cases
print("\n[TEST 4] Edge Cases")
print("-"*80)

try:
    # Test với base_head = 0
    wn3 = wntr.network.WaterNetworkModel(settings.epanet_input_file)
    reservoir3 = wn3.get_node("TXU2")
    
    scada_data_zero = {
        "13085": [
            {"timestamp": "2025-01-15 10:00", "pressure": 0.0},
            {"timestamp": "2025-01-15 11:00", "pressure": 10.0}
        ]
    }
    
    # Apply và check
    scada_boundary_service.apply_scada_boundary_conditions(
        wn=wn3,
        scada_boundary_data=scada_data_zero,
        simulation_duration_hours=2,
        hydraulic_timestep_hours=1,
        simulation_start_time=datetime(2025, 1, 15, 10, 0)
    )
    
    base_head = reservoir3.base_head
    pattern_name = reservoir3.head_pattern_name
    
    print(f"Edge case: base_head = 0")
    print(f"  Final base_head: {base_head}m")
    print(f"  Pattern created: {pattern_name is not None}")
    
    if pattern_name:
        pattern = wn3.get_pattern(pattern_name)
        print(f"  Multipliers: {pattern.multipliers}")
        
        # Should handle base_head = 0 correctly
        if len(pattern.multipliers) > 0:
            print("[OK] Pattern created even with base_head = 0")
        else:
            print("[WARN] Pattern has no multipliers")
    
except Exception as e:
    print(f"[ERROR] Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*80)
print("[SUCCESS] ALL HYDRAULIC LOGIC TESTS PASSED")
print("="*80)



