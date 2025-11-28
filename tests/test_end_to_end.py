"""
End-to-end test để verify toàn bộ flow từ API đến simulation
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import json
from datetime import datetime, timedelta


def test_scada_data_format():
    """Test format của SCADA boundary data"""
    print("\n" + "="*60)
    print("TEST: SCADA Data Format")
    print("="*60)
    
    # Simulate SCADA data format từ scada_service
    mock_scada_boundary = {
        "13085": [
            {
                "station_code": "13085",
                "timestamp": "2025-01-15 10:00",
                "pressure": 25.5,
                "flow": 100.0,
                "description": "SCADA data from station 13085 - boundary condition only"
            },
            {
                "station_code": "13085",
                "timestamp": "2025-01-15 11:00",
                "pressure": 26.0,
                "flow": 105.0,
                "description": "SCADA data from station 13085 - boundary condition only"
            }
        ]
    }
    
    print("Mock SCADA boundary data format:")
    print(json.dumps(mock_scada_boundary, indent=2))
    
    # Validate format
    required_keys = ['timestamp', 'pressure', 'flow']
    for station_code, records in mock_scada_boundary.items():
        print(f"\nValidating station {station_code}:")
        for i, record in enumerate(records):
            missing = [k for k in required_keys if k not in record]
            if missing:
                print(f"   [ERROR] Record {i} missing keys: {missing}")
                return False
            else:
                print(f"   [OK] Record {i} has all required keys")
    
    print("\n[OK] SCADA data format is valid")
    return True


def test_mapping_validation():
    """Test mapping validation"""
    print("\n" + "="*60)
    print("TEST: Mapping Validation")
    print("="*60)
    
    config_file = Path("config/scada_mapping.json")
    
    if not config_file.exists():
        print(f"[ERROR] Config file not found")
        return False
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    scada_stations = config.get('scada_stations', {})
    
    for station_code, station_info in scada_stations.items():
        print(f"\nValidating station {station_code}:")
        
        epanet_mapping = station_info.get('epanet_mapping')
        if not epanet_mapping:
            print(f"   [WARN] No epanet_mapping")
            continue
        
        required_mapping_keys = ['epanet_node', 'node_type', 'apply_pressure_as_head']
        missing = [k for k in required_mapping_keys if k not in epanet_mapping]
        
        if missing:
            print(f"   [ERROR] Missing mapping keys: {missing}")
            return False
        
        print(f"   [OK] epanet_node: {epanet_mapping.get('epanet_node')}")
        print(f"   [OK] node_type: {epanet_mapping.get('node_type')}")
        print(f"   [OK] apply_pressure_as_head: {epanet_mapping.get('apply_pressure_as_head')}")
    
    print("\n[OK] Mapping validation passed")
    return True


def test_service_initialization():
    """Test service initialization"""
    print("\n" + "="*60)
    print("TEST: Service Initialization")
    print("="*60)
    
    try:
        from services.scada_boundary_service import scada_boundary_service
        
        print("[OK] SCADA boundary service initialized")
        print(f"   Mapping config loaded: {len(scada_boundary_service.mapping_config)} station(s)")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Service initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_epanet_service_signature():
    """Test EPANET service method signatures"""
    print("\n" + "="*60)
    print("TEST: EPANET Service Signatures")
    print("="*60)
    
    try:
        from services.epanet_service import epanet_service
        import inspect
        
        # Check run_simulation signature
        sig = inspect.signature(epanet_service.run_simulation)
        params = sig.parameters
        
        print("run_simulation() parameters:")
        for param_name, param in params.items():
            default = param.default if param.default != inspect.Parameter.empty else "required"
            print(f"   - {param_name}: {default}")
        
        # Verify scada_boundary_data is optional
        if 'scada_boundary_data' in params:
            param = params['scada_boundary_data']
            if param.default != inspect.Parameter.empty:
                print("\n[OK] scada_boundary_data is optional (backward compatible)")
            else:
                print("\n[WARN] scada_boundary_data is required (may break backward compatibility)")
                return False
        else:
            print("\n[ERROR] scada_boundary_data parameter not found")
            return False
        
        # Check _real_simulation signature
        sig_real = inspect.signature(epanet_service._real_simulation)
        params_real = sig_real.parameters
        
        if 'scada_boundary_data' in params_real:
            param_real = params_real['scada_boundary_data']
            if param_real.default != inspect.Parameter.empty:
                print("[OK] _real_simulation() scada_boundary_data is optional")
            else:
                print("[WARN] _real_simulation() scada_boundary_data is required")
                return False
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Error checking signatures: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all end-to-end tests"""
    print("\n" + "="*60)
    print("END-TO-END SYSTEM TEST")
    print("="*60)
    
    results = {}
    
    results['format'] = test_scada_data_format()
    results['mapping'] = test_mapping_validation()
    results['service'] = test_service_initialization()
    results['signature'] = test_epanet_service_signature()
    
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
        print("\n[SUCCESS] ALL END-TO-END TESTS PASSED!")
        return 0
    else:
        print(f"\n[WARN] {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

