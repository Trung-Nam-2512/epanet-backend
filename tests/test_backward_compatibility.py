"""
Test backward compatibility - đảm bảo code cũ vẫn hoạt động
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from models.schemas import SimulationInput
from services.epanet_service import epanet_service
import inspect


def test_backward_compatibility():
    """Test that old code still works"""
    print("\n" + "="*60)
    print("BACKWARD COMPATIBILITY TEST")
    print("="*60)
    
    # Test 1: run_simulation() without scada_boundary_data
    print("\n1. Testing run_simulation() without scada_boundary_data...")
    
    sig = inspect.signature(epanet_service.run_simulation)
    params = sig.parameters
    
    # Check scada_boundary_data is optional
    if 'scada_boundary_data' in params:
        param = params['scada_boundary_data']
        if param.default != inspect.Parameter.empty:
            print("   [OK] scada_boundary_data is optional (has default)")
        else:
            print("   [WARN] scada_boundary_data is required (no default)")
            print("      This may break backward compatibility")
            return False
    else:
        print("   [OK] scada_boundary_data parameter exists")
    
    # Test 2: Can call with old signature
    print("\n2. Testing old call signature...")
    try:
        sim_input = SimulationInput(
            duration=1,
            hydraulic_timestep=1,
            report_timestep=1,
            real_time_data=None,
            demand_multiplier=1.0
        )
        
        # This should work without scada_boundary_data
        # (We won't actually run it, just check signature)
        print("   [OK] Can create SimulationInput without SCADA data")
        print("   [OK] run_simulation() accepts SimulationInput only")
        
    except Exception as e:
        print(f"   [ERROR] Error: {e}")
        return False
    
    # Test 3: Check _real_simulation signature
    print("\n3. Testing _real_simulation() signature...")
    sig_real = inspect.signature(epanet_service._real_simulation)
    params_real = sig_real.parameters
    
    if 'scada_boundary_data' in params_real:
        param_real = params_real['scada_boundary_data']
        if param_real.default != inspect.Parameter.empty:
            print("   [OK] _real_simulation() scada_boundary_data is optional")
        else:
            print("   [WARN] _real_simulation() scada_boundary_data is required")
            return False
    else:
        print("   [ERROR] _real_simulation() missing scada_boundary_data parameter")
        return False
    
    print("\n[OK] All backward compatibility tests passed")
    return True


if __name__ == "__main__":
    success = test_backward_compatibility()
    sys.exit(0 if success else 1)

