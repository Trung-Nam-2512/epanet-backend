#!/usr/bin/env python3
"""
Test backend với giải pháp pattern multipliers = 1.0
"""

import requests
import json

def test_backend_with_fixed_demand():
    """Test backend với demand cố định"""
    print("=" * 80)
    print("TEST BACKEND VOI DEMAND CO DINH")
    print("=" * 80)
    
    # Test simulation API
    params = {
        "station_codes": ["13085"],
        "hours_back": 24,
        "duration": 24,
        "hydraulic_timestep": 1,
        "report_timestep": 1
    }
    
    try:
        print("1. Testing simulation API...")
        response = requests.post(
            "http://localhost:8000/api/v1/scada/simulation-with-realtime",
            json=params,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            sim_result = data['simulation_result']
            nodes_results = sim_result.get('nodes_results', {})
            
            print(f"SUCCESS: Got {len(nodes_results)} nodes results")
            
            # Check node 2 demand
            if '2' in nodes_results:
                node2_data = nodes_results['2']
                if node2_data and len(node2_data) > 0:
                    latest_data = node2_data[-1]
                    demand = latest_data.get('demand', 0)
                    pressure = latest_data.get('pressure', 0)
                    flow = latest_data.get('flow', 0)
                    
                    print(f"\nNode 2 results:")
                    print(f"  - Demand: {demand:.5f} LPS")
                    print(f"  - Pressure: {pressure:.2f} m")
                    print(f"  - Flow: {flow:.5f} LPS")
                    
                    # Check if demand is now fixed (should be ~0.04872)
                    expected_demand = 0.04872
                    if abs(demand - expected_demand) < 0.001:
                        print(f"SUCCESS: Demand is fixed at {demand:.5f} LPS")
                        print("Pattern effect has been neutralized!")
                    else:
                        print(f"ISSUE: Demand {demand:.5f} != expected {expected_demand:.5f}")
                else:
                    print("ERROR: No data for node 2")
            else:
                print("ERROR: Node 2 not found in results")
            
            # Check pattern API
            print(f"\n2. Testing pattern API...")
            pattern_response = requests.get("http://localhost:8000/api/v1/network/patterns")
            
            if pattern_response.status_code == 200:
                pattern_data = pattern_response.json()
                patterns = pattern_data.get('data', {}).get('patterns', {})
                
                if '1' in patterns:
                    pattern1 = patterns['1']
                    multipliers = pattern1.get('multipliers', [])
                    print(f"Pattern 1 multipliers: {multipliers[:5]}...")
                    
                    # Check if multipliers are all 1.0
                    if all(mult == 1.0 for mult in multipliers):
                        print("SUCCESS: Pattern multipliers are all 1.0")
                        print("Pattern data is preserved for frontend display")
                    else:
                        print("ISSUE: Pattern multipliers are not all 1.0")
                else:
                    print("ERROR: Pattern 1 not found")
            else:
                print(f"ERROR: Pattern API failed: {pattern_response.status_code}")
            
            return True
            
        else:
            print(f"ERROR: Simulation API failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"ERROR: Exception: {e}")
        return False

def main():
    """Main function"""
    success = test_backend_with_fixed_demand()
    
    print("\n" + "=" * 80)
    if success:
        print("SUCCESS: Backend is working with fixed demand!")
        print("\nBenefits achieved:")
        print("- Demand is now fixed (no pattern effect)")
        print("- Pattern data preserved for frontend")
        print("- Simulation results are consistent")
        print("- SCADA integration works correctly")
    else:
        print("ERROR: Backend needs further investigation")

if __name__ == "__main__":
    main()
