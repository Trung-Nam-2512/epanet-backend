#!/usr/bin/env python3
"""
Script để kiểm tra cấu trúc API response chi tiết
"""

import requests
import json

def check_api_structure():
    """Kiểm tra cấu trúc API response chi tiết"""
    print("Checking API Response Structure Details")
    print("=" * 50)
    
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
            
            print("\nResponse Structure Analysis:")
            print(f"- Type: {type(data)}")
            print(f"- Keys: {list(data.keys())}")
            
            print("\nTop-level structure:")
            for key, value in data.items():
                if key == 'simulation_result' and isinstance(value, dict):
                    print(f"- {key}: dict with keys: {list(value.keys())}")
                    print(f"  - nodes_results: {len(value.get('nodes_results', {}))} nodes")
                    print(f"  - pipes_results: {len(value.get('pipes_results', {}))} pipes")
                elif key == 'scada_summary' and isinstance(value, dict):
                    print(f"- {key}: dict with keys: {list(value.keys())}")
                else:
                    print(f"- {key}: {type(value)} = {value}")
            
            # Check if the response has the expected structure
            print("\nStructure Check:")
            has_success = 'success' in data
            has_message = 'message' in data
            has_simulation_result = 'simulation_result' in data
            has_scada_summary = 'scada_summary' in data
            
            print(f"- Has 'success': {has_success}")
            print(f"- Has 'message': {has_message}")
            print(f"- Has 'simulation_result': {has_simulation_result}")
            print(f"- Has 'scada_summary': {has_scada_summary}")
            
            if has_simulation_result:
                sim_result = data['simulation_result']
                print(f"- simulation_result type: {type(sim_result)}")
                print(f"- simulation_result keys: {list(sim_result.keys()) if isinstance(sim_result, dict) else 'Not a dict'}")
                
                if isinstance(sim_result, dict) and 'nodes_results' in sim_result:
                    nodes_results = sim_result['nodes_results']
                    print(f"- nodes_results type: {type(nodes_results)}")
                    print(f"- nodes_results keys: {list(nodes_results.keys())[:5]}... (showing first 5)")
                    
                    # Show sample node data
                    if nodes_results:
                        first_node_id = list(nodes_results.keys())[0]
                        first_node_data = nodes_results[first_node_id]
                        print(f"- Sample node data ({first_node_id}): {first_node_data[0] if first_node_data else 'No data'}")
            
            return data
        else:
            print(f"Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"Exception: {e}")
        return None

if __name__ == "__main__":
    check_api_structure()
