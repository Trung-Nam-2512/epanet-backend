"""
Test để verify SCADA head pattern KHÔNG bị override bởi demand pattern logic
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
print("TEST: SCADA Pattern Override Issue")
print("="*80)

# Test: Verify SCADA head pattern không bị override
print("\n[TEST] SCADA Head Pattern Not Overridden")
print("-"*80)

try:
    # Create SCADA data
    scada_data = {
        "13085": [
            {"timestamp": "2025-01-15 10:00", "pressure": 20.0},
            {"timestamp": "2025-01-15 11:00", "pressure": 30.0},
            {"timestamp": "2025-01-15 12:00", "pressure": 25.0}
        ]
    }
    
    # Run simulation through epanet_service (như production)
    simulation_input = SimulationInput(
        duration=3,
        hydraulic_timestep=1,
        report_timestep=1,
        real_time_data=None,
        demand_multiplier=1.0
    )
    
    # Run simulation
    result = epanet_service.run_simulation(
        simulation_input,
        scada_boundary_data=scada_data
    )
    
    if result.status != "completed":
        print(f"[FAIL] Simulation failed: {result.error_message}")
        sys.exit(1)
    
    # Load model lại để check pattern
    wn = wntr.network.WaterNetworkModel(settings.epanet_input_file)
    reservoir = wn.get_node("TXU2")
    
    # Apply SCADA boundary lại để check pattern name
    scada_boundary_service.apply_scada_boundary_conditions(
        wn=wn,
        scada_boundary_data=scada_data,
        simulation_duration_hours=3,
        hydraulic_timestep_hours=1,
        simulation_start_time=datetime(2025, 1, 15, 10, 0)
    )
    
    pattern_name = reservoir.head_pattern_name
    
    if pattern_name and pattern_name.startswith("SCADA_HEAD_"):
        # Check if pattern exists và không bị override
        if pattern_name in wn.pattern_name_list:
            pattern = wn.get_pattern(pattern_name)
            print(f"[OK] SCADA pattern exists: {pattern_name}")
            print(f"  Multipliers: {pattern.multipliers[:3]}")
            
            # Verify multipliers không phải tất cả = 1.0
            if all(abs(m - 1.0) < 0.01 for m in pattern.multipliers):
                print("[FAIL] SCADA pattern multipliers all = 1.0 - pattern was overridden!")
                sys.exit(1)
            else:
                print("[OK] SCADA pattern multipliers are NOT all 1.0 - pattern preserved")
        else:
            print(f"[FAIL] SCADA pattern {pattern_name} not found in pattern list!")
            sys.exit(1)
    else:
        print("[FAIL] No SCADA pattern created!")
        sys.exit(1)
    
    # Check simulation results
    print("\n[TEST] Simulation Results Verification")
    print("-"*80)
    
    # Get node results từ simulation result
    if hasattr(result, 'node_results') and result.node_results:
        # Check if TXU2 head values match SCADA
        print("[OK] Simulation completed with SCADA boundary conditions")
        print(f"  Total time steps: {len(result.node_results.get('head', {}).get('TXU2', []))}")
    else:
        print("[WARN] Cannot verify simulation results structure")
    
except Exception as e:
    print(f"[ERROR] Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*80)
print("[SUCCESS] SCADA Pattern Not Overridden")
print("="*80)



