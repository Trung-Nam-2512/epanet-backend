#!/usr/bin/env python3
"""
Script để test frontend có nhận được dữ liệu đúng không
"""

import requests
import json

def test_frontend_data_reception():
    """Test xem frontend có nhận được dữ liệu đúng không"""
    print("Testing Frontend Data Reception")
    print("=" * 50)
    
    # Test simulation API
    params = {
        "station_codes": ["13085"],
        "hours_back": 24,
        "duration": 24,
        "hydraulic_timestep": 1,
        "report_timestep": 1
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/scada/simulation-with-realtime",
            json=params,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print("\nAPI Response Structure:")
            print(f"- success: {data.get('success')}")
            print(f"- message: {data.get('message')}")
            print(f"- has simulation_result: {'simulation_result' in data}")
            print(f"- has scada_summary: {'scada_summary' in data}")
            
            if 'simulation_result' in data:
                sim_result = data['simulation_result']
                print(f"\nSimulation Result:")
                print(f"- status: {sim_result.get('status')}")
                print(f"- duration: {sim_result.get('duration')}")
                print(f"- nodes_results count: {len(sim_result.get('nodes_results', {}))}")
                print(f"- pipes_results count: {len(sim_result.get('pipes_results', {}))}")
                
                # Check if frontend can access the data
                print(f"\nFrontend Data Access Test:")
                print(f"- data.success: {data.get('success')}")
                print(f"- data.simulation_result: {'simulation_result' in data}")
                print(f"- data.simulation_result.nodes_results: {'nodes_results' in sim_result}")
                
                if 'nodes_results' in sim_result:
                    nodes_results = sim_result['nodes_results']
                    sample_node_id = list(nodes_results.keys())[0]
                    sample_data = nodes_results[sample_node_id][0] if nodes_results[sample_node_id] else None
                    
                    print(f"- Sample node data ({sample_node_id}):")
                    if sample_data:
                        print(f"  - pressure: {sample_data.get('pressure', 0):.2f}")
                        print(f"  - flow: {sample_data.get('flow', 0):.2f}")
                        print(f"  - head: {sample_data.get('head', 0):.2f}")
                        print(f"  - demand: {sample_data.get('demand', 0):.2f}")
                    
                    # Test frontend data processing
                    print(f"\nFrontend Processing Test:")
                    print(f"- Node IDs available: {list(nodes_results.keys())[:5]}...")
                    print(f"- Can access node '2': {'2' in nodes_results}")
                    print(f"- Can access node '3': {'3' in nodes_results}")
                    
                    if '2' in nodes_results:
                        node2_data = nodes_results['2']
                        if node2_data and len(node2_data) > 0:
                            latest_data = node2_data[-1]
                            print(f"- Node 2 latest data: pressure={latest_data.get('pressure', 0):.2f}, flow={latest_data.get('flow', 0):.2f}")
                
                print(f"\n✅ Frontend should be able to process this data correctly!")
                return True
            else:
                print(f"❌ No simulation_result in response")
                return False
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def main():
    """Main test function"""
    success = test_frontend_data_reception()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ SUCCESS: Frontend should work correctly now!")
        print("\nNext steps:")
        print("1. Open frontend in browser")
        print("2. Run simulation with station code '13085'")
        print("3. Check browser console for any errors")
        print("4. Verify nodes change colors and tooltips work")
    else:
        print("❌ FAILED: Frontend won't work correctly")
        print("\nIssues to fix:")
        print("1. Check API endpoints")
        print("2. Verify data structure")
        print("3. Check frontend data processing logic")

if __name__ == "__main__":
    main()
