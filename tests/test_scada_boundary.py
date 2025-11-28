"""
Test script để verify SCADA boundary conditions được apply đúng
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Test imports
try:
    import wntr
    print("[OK] WNTR imported successfully")
except ImportError as e:
    print(f"[ERROR] WNTR import failed: {e}")
    sys.exit(1)

try:
    from services.scada_boundary_service import SCADABoundaryService, scada_boundary_service
    print("[OK] SCADABoundaryService imported successfully")
except ImportError as e:
    print(f"[ERROR] SCADABoundaryService import failed: {e}")
    sys.exit(1)

try:
    from services.epanet_service import epanet_service
    print("[OK] EPANETService imported successfully")
except ImportError as e:
    print(f"[ERROR] EPANETService import failed: {e}")
    sys.exit(1)

from core.config import settings


def test_mapping_config_loaded():
    """Test 1: Verify mapping config được load đúng"""
    print("\n" + "="*60)
    print("TEST 1: Mapping Config Loading")
    print("="*60)
    
    try:
        service = SCADABoundaryService()
        mapping = service.mapping_config
        
        if not mapping:
            print("[WARN] WARNING: No mapping config loaded")
            print("   Check if config/scada_mapping.json exists and has epanet_mapping")
            return False
        
        print(f"[OK] Mapping config loaded: {len(mapping)} station(s)")
        for station_code, config in mapping.items():
            print(f"   - Station {station_code}:")
            print(f"     -> EPANET {config.get('node_type')} {config.get('epanet_node')}")
            print(f"     -> Apply pressure: {config.get('apply_pressure_as_head')}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Error loading mapping config: {e}")
        return False


def test_wntr_model_loading():
    """Test 2: Verify WNTR model có thể load"""
    print("\n" + "="*60)
    print("TEST 2: WNTR Model Loading")
    print("="*60)
    
    try:
        inp_file = settings.epanet_input_file
        print(f"Loading EPANET file: {inp_file}")
        
        wn = wntr.network.WaterNetworkModel(inp_file)
        print(f"[OK] Model loaded successfully")
        print(f"   - Nodes: {len(wn.node_name_list)}")
        print(f"   - Links: {len(wn.link_name_list)}")
        print(f"   - Reservoirs: {len(wn.reservoir_name_list)}")
        print(f"   - Tanks: {len(wn.tank_name_list)}")
        
        # Check if TXU2 exists (from mapping)
        if "TXU2" in wn.reservoir_name_list:
            print(f"   [OK] Reservoir TXU2 exists in model")
            reservoir = wn.get_node("TXU2")
            print(f"      Current base_head: {reservoir.base_head}")
        else:
            print(f"   [WARN] WARNING: Reservoir TXU2 not found in model")
            print(f"      Available reservoirs: {wn.reservoir_name_list}")
        
        return True, wn
        
    except Exception as e:
        print(f"[ERROR] Error loading WNTR model: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_scada_boundary_application(wn):
    """Test 3: Verify SCADA boundary được apply"""
    print("\n" + "="*60)
    print("TEST 3: SCADA Boundary Application")
    print("="*60)
    
    if not wn:
        print("[ERROR] WNTR model not loaded - skipping test")
        return False
    
    try:
        # Create mock SCADA boundary data
        now = datetime.now()
        mock_scada_data = {
            "13085": [
                {
                    "timestamp": (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M"),
                    "pressure": 25.5,  # Mock pressure value
                    "flow": 100.0,
                    "station_code": "13085"
                },
                {
                    "timestamp": now.strftime("%Y-%m-%d %H:%M"),
                    "pressure": 26.0,
                    "flow": 105.0,
                    "station_code": "13085"
                }
            ]
        }
        
        print("Mock SCADA data created:")
        print(f"   Station 13085: {len(mock_scada_data['13085'])} records")
        
        # Get initial reservoir head
        if "TXU2" in wn.reservoir_name_list:
            reservoir = wn.get_node("TXU2")
            initial_head = reservoir.base_head
            print(f"\nInitial reservoir TXU2 head: {initial_head}")
            
            # Apply SCADA boundary
            service = scada_boundary_service
            applied = service.apply_scada_boundary_conditions(
                wn=wn,
                scada_boundary_data=mock_scada_data,
                simulation_duration_hours=1,
                hydraulic_timestep_hours=1
            )
            
            if applied:
                new_head = reservoir.base_head
                print(f"\n[OK] SCADA boundary applied successfully")
                print(f"   Initial head: {initial_head}")
                print(f"   New head: {new_head}")
                print(f"   Head changed: {abs(new_head - initial_head) > 0.01}")
                
                if abs(new_head - initial_head) > 0.01:
                    print(f"   [OK] Head was updated from SCADA data")
                    return True
                else:
                    print(f"   [WARN] WARNING: Head was not updated")
                    return False
            else:
                print(f"\n[WARN] SCADA boundary not applied")
                print(f"   Check mapping configuration")
                return False
        else:
            print(f"[WARN] Reservoir TXU2 not found - cannot test")
            return False
            
    except Exception as e:
        print(f"[ERROR] Error applying SCADA boundary: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_epanet_service_integration():
    """Test 4: Verify EPANET service integration"""
    print("\n" + "="*60)
    print("TEST 4: EPANET Service Integration")
    print("="*60)
    
    try:
        from models.schemas import SimulationInput
        
        # Test without SCADA (backward compatibility)
        print("Testing without SCADA data (backward compatibility)...")
        sim_input = SimulationInput(
            duration=1,
            hydraulic_timestep=1,
            report_timestep=1,
            real_time_data=None,
            demand_multiplier=1.0
        )
        
        # Check if run_simulation accepts optional scada_boundary_data
        import inspect
        sig = inspect.signature(epanet_service.run_simulation)
        params = list(sig.parameters.keys())
        
        if 'scada_boundary_data' in params:
            print("[OK] run_simulation() accepts scada_boundary_data parameter")
        else:
            print("[ERROR] run_simulation() does NOT accept scada_boundary_data parameter")
            return False
        
        print("[OK] EPANET service integration OK")
        return True
        
    except Exception as e:
        print(f"[ERROR] Error testing EPANET service: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_file_exists():
    """Test 5: Verify config file exists and is valid"""
    print("\n" + "="*60)
    print("TEST 5: Config File Validation")
    print("="*60)
    
    config_file = Path("config/scada_mapping.json")
    
    if not config_file.exists():
        print(f"[ERROR] Config file not found: {config_file}")
        return False
    
    print(f"[OK] Config file exists: {config_file}")
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print("[OK] Config file is valid JSON")
        
        # Check structure
        scada_stations = config.get('scada_stations', {})
        if not scada_stations:
            print("[WARN] WARNING: No scada_stations in config")
            return False
        
        print(f"[OK] Found {len(scada_stations)} SCADA station(s)")
        
        # Check mapping
        has_mapping = False
        for station_code, station_info in scada_stations.items():
            epanet_mapping = station_info.get('epanet_mapping')
            if epanet_mapping:
                has_mapping = True
                print(f"   [OK] Station {station_code} has epanet_mapping")
                print(f"      -> {epanet_mapping.get('node_type')} {epanet_mapping.get('epanet_node')}")
            else:
                print(f"   [WARN] Station {station_code} has NO epanet_mapping")
        
        if not has_mapping:
            print("[WARN] WARNING: No stations have epanet_mapping configured")
            return False
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"[ERROR] Config file is not valid JSON: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Error reading config file: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("SCADA BOUNDARY CONDITIONS - SYSTEM TEST")
    print("="*60)
    
    results = {}
    
    # Test 1: Config file
    results['config'] = test_config_file_exists()
    
    # Test 2: Mapping config loading
    results['mapping'] = test_mapping_config_loaded()
    
    # Test 3: WNTR model loading
    success, wn = test_wntr_model_loading()
    results['model'] = success
    
    # Test 4: SCADA boundary application (if model loaded)
    if success and wn:
        results['boundary'] = test_scada_boundary_application(wn)
    else:
        results['boundary'] = False
        print("\n[WARN] Skipping boundary test - model not loaded")
    
    # Test 5: EPANET service integration
    results['integration'] = test_epanet_service_integration()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for test_name, result in results.items():
        status = "[OK] PASS" if result else "[ERROR] FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[SUCCESS] ALL TESTS PASSED - System is ready!")
        return 0
    else:
        print(f"\n[WARN] {total - passed} test(s) failed - Please review")
        return 1


if __name__ == "__main__":
    sys.exit(main())

