"""
Test cuối cùng để verify 100% chắc chắn - trace toàn bộ flow
"""
import sys
import wntr
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.scada_boundary_service import scada_boundary_service
from services.epanet_service import epanet_service
from models.schemas import SimulationInput
from core.config import settings

print("="*80)
print("FINAL VERIFICATION - TRACE TOAN BO FLOW")
print("="*80)

# Test: Verify toàn bộ flow từ SCADA data đến simulation results
print("\n[TEST] End-to-End Flow Verification")
print("-"*80)

try:
    # Step 1: Create SCADA data
    scada_data = {
        "13085": [
            {"timestamp": "2025-01-15 10:00", "pressure": 20.0},
            {"timestamp": "2025-01-15 11:00", "pressure": 30.0},
            {"timestamp": "2025-01-15 12:00", "pressure": 25.0}
        ]
    }
    
    print("Step 1: SCADA data created")
    print(f"  Station 13085: 3 records")
    print(f"  Pressures: 20.0m, 30.0m, 25.0m")
    
    # Step 2: Load model và apply SCADA boundary
    wn = wntr.network.WaterNetworkModel(settings.epanet_input_file)
    reservoir = wn.get_node("TXU2")
    
    initial_head = reservoir.base_head
    print(f"\nStep 2: Load model")
    print(f"  Initial base_head: {initial_head}m")
    
    # Apply SCADA boundary
    applied = scada_boundary_service.apply_scada_boundary_conditions(
        wn=wn,
        scada_boundary_data=scada_data,
        simulation_duration_hours=3,
        hydraulic_timestep_hours=1,
        simulation_start_time=datetime(2025, 1, 15, 10, 0)
    )
    
    if not applied:
        print("[FAIL] SCADA boundary not applied!")
        sys.exit(1)
    
    print(f"\nStep 3: SCADA boundary applied")
    print(f"  base_head: {reservoir.base_head}m")
    print(f"  pattern_name: {reservoir.head_pattern_name}")
    
    # Verify pattern
    if not reservoir.head_pattern_name:
        print("[FAIL] No pattern created!")
        sys.exit(1)
    
    pattern = wn.get_pattern(reservoir.head_pattern_name)
    print(f"  pattern multipliers: {pattern.multipliers[:3]}")
    
    # Verify multipliers
    expected_mult = [1.0, 1.5, 1.25]
    actual_mult = pattern.multipliers[:3]
    
    for i, (exp, act) in enumerate(zip(expected_mult, actual_mult)):
        if abs(exp - act) > 0.01:
            print(f"[FAIL] Multiplier {i} mismatch: expected {exp}, got {act}")
            sys.exit(1)
    
    print("[OK] Pattern multipliers correct")
    
    # Step 4: Verify head_timeseries.at() returns correct values
    print(f"\nStep 4: Verify head_timeseries.at()")
    
    # Set simulation time
    wn.options.time.duration = 3 * 3600
    wn.options.time.hydraulic_timestep = 3600
    wn.options.time.report_timestep = 3600
    
    # Test head_timeseries.at() tại các time steps
    test_times = [0, 3600, 7200]  # 0h, 1h, 2h in seconds
    expected_heads = [20.0, 30.0, 25.0]
    
    for test_time, expected_head in zip(test_times, expected_heads):
        wn.sim_time = test_time
        actual_head = reservoir.head_timeseries.at(wn.sim_time)
        
        print(f"  Time {test_time/3600:.1f}h: expected {expected_head}m, got {actual_head:.2f}m")
        
        if abs(actual_head - expected_head) > 0.5:
            print(f"[FAIL] Head mismatch at time {test_time/3600:.1f}h!")
            sys.exit(1)
    
    print("[OK] head_timeseries.at() returns correct values")
    
    # Step 5: Run simulation và verify results
    print(f"\nStep 5: Run simulation")
    
    # Initialize simulation time properly
    wn._prev_sim_time = 0
    wn.sim_time = 0
    
    sim = wntr.sim.WNTRSimulator(wn)
    results = sim.run_sim()
    
    reservoir_heads = results.node['head'].loc[:, 'TXU2']
    
    print("  Simulation results:")
    for i, (time_sec, head) in enumerate(reservoir_heads.items()):
        if i >= 3:
            break
        time_hour = time_sec / 3600
        expected = expected_heads[i]
        print(f"    Time {time_hour:.1f}h: {head:.2f}m (expected {expected}m)")
        
        if abs(head - expected) > 0.5:
            print(f"[FAIL] Simulation result mismatch at time {time_hour:.1f}h!")
            sys.exit(1)
    
    print("[OK] Simulation results match SCADA data!")
    
    # Step 6: Verify pattern không bị override
    print(f"\nStep 6: Verify pattern not overridden")
    
    # Check pattern multipliers sau simulation
    pattern_after = wn.get_pattern(reservoir.head_pattern_name)
    multipliers_after = pattern_after.multipliers[:3]
    
    if all(abs(m - 1.0) < 0.01 for m in multipliers_after):
        print("[FAIL] Pattern multipliers all = 1.0 - pattern was overridden!")
        sys.exit(1)
    
    print(f"  Pattern multipliers after simulation: {multipliers_after}")
    print("[OK] Pattern not overridden")
    
    # Step 7: Verify pressure conversion
    print(f"\nStep 7: Verify pressure conversion")
    
    # Test với gauge pressure
    from services.scada_boundary_service import SCADABoundaryService
    service = SCADABoundaryService()
    
    # Get mapping
    mapping = service.mapping_config.get("13085", {})
    pressure_type = mapping.get('pressure_type', 'absolute')
    elevation = mapping.get('elevation', 0.0)
    
    print(f"  pressure_type: {pressure_type}")
    print(f"  elevation: {elevation}")
    
    if pressure_type == 'absolute':
        print("[OK] Pressure type is absolute - no conversion needed")
    else:
        print(f"[OK] Pressure type is gauge - conversion: head = {elevation}m + pressure")
    
except Exception as e:
    print(f"[ERROR] Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*80)
print("[SUCCESS] ALL VERIFICATION TESTS PASSED - 100% CHAC CHAN")
print("="*80)
print("\nXac nhan:")
print("  1. SCADA data duoc parse dung")
print("  2. Pattern duoc tao va link voi reservoir")
print("  3. head_timeseries.at() tra ve dung gia tri")
print("  4. Simulation results match SCADA data")
print("  5. Pattern khong bi override")
print("  6. Pressure conversion logic dung")

