#!/usr/bin/env python3
"""
Script để test API và debug vấn đề với frontend
"""

import requests
import json
import sys
from datetime import datetime, timedelta

# API Configuration
API_BASE_URL = "http://localhost:8000"

def test_network_topology():
    """Test API lấy network topology"""
    print("Testing Network Topology API...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/network/topology")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data.get('success', False)}")
            print(f"Nodes: {len(data.get('data', {}).get('nodes', []))}")
            print(f"Pipes: {len(data.get('data', {}).get('pipes', []))}")
            
            # Show sample data
            if data.get('data', {}).get('nodes'):
                sample_node = data['data']['nodes'][0]
                print(f"Sample Node: {sample_node}")
            
            return data
        else:
            print(f"Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"Exception: {e}")
        return None

def test_simulation_api():
    """Test API simulation"""
    print("\nTesting Simulation API...")
    
    # Test parameters
    params = {
        "station_codes": ["13085"],  # Use correct station code from mapping
        "hours_back": 24,
        "duration": 24,
        "hydraulic_timestep": 1,
        "report_timestep": 1
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/scada/simulation-with-realtime",
            json=params,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data.get('success', False)}")
            print(f"Message: {data.get('message', 'No message')}")
            
            if data.get('simulation_result'):
                sim_result = data['simulation_result']
                print(f"Simulation Status: {sim_result.get('status', 'Unknown')}")
                print(f"Nodes Results Keys: {list(sim_result.get('nodes_results', {}).keys())}")
                print(f"Pipes Results Keys: {list(sim_result.get('pipes_results', {}).keys())}")
                
                # Show sample node data
                nodes_results = sim_result.get('nodes_results', {})
                if nodes_results:
                    first_node_id = list(nodes_results.keys())[0]
                    first_node_data = nodes_results[first_node_id]
                    print(f"Sample Node Data ({first_node_id}): {first_node_data[0] if first_node_data else 'No data'}")
                
                return data
            else:
                print("No simulation_result in response")
                return None
        else:
            print(f"Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"Exception: {e}")
        return None

def test_scada_data():
    """Test SCADA data API"""
    print("\nTesting SCADA Data API...")
    
    params = {
        "station_codes": ["13085"],  # Use correct station code from mapping
        "hours_back": 24
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/scada/realtime",
            json=params,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data.get('success', False)}")
            print(f"Message: {data.get('message', 'No message')}")
            
            if data.get('data'):
                scada_data = data['data']
                print(f"SCADA Summary: {scada_data.get('summary', {})}")
                
                epanet_data = scada_data.get('epanet_data', {})
                print(f"EPANET Data Keys: {list(epanet_data.keys())}")
                
                if epanet_data:
                    first_station = list(epanet_data.keys())[0]
                    first_data = epanet_data[first_station]
                    print(f"Sample EPANET Data ({first_station}): {first_data[0] if first_data else 'No data'}")
                
                return data
            else:
                print("No data in response")
                return None
        else:
            print(f"Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"Exception: {e}")
        return None

def main():
    """Main test function"""
    print("EPANET API Debug Tool")
    print("=" * 50)
    
    # Test 1: Network Topology
    topology_data = test_network_topology()
    
    # Test 2: SCADA Data
    scada_data = test_scada_data()
    
    # Test 3: Simulation
    simulation_data = test_simulation_api()
    
    # Summary
    print("\nSummary:")
    print(f"Network Topology: {'OK' if topology_data else 'FAILED'}")
    print(f"SCADA Data: {'OK' if scada_data else 'FAILED'}")
    print(f"Simulation: {'OK' if simulation_data else 'FAILED'}")
    
    # Recommendations
    print("\nRecommendations:")
    if not topology_data:
        print("- Check if backend is running on port 8000")
        print("- Check network topology API endpoint")
    
    if not scada_data:
        print("- Check SCADA API configuration")
        print("- Verify SCADA token and URL")
    
    if not simulation_data:
        print("- Check EPANET service configuration")
        print("- Verify input file (epanet.inp) exists")
        print("- Check WNTR library installation")
    
    if topology_data and scada_data and simulation_data:
        print("- All APIs working! Check frontend data processing")
        print("- Verify data structure matches frontend expectations")

if __name__ == "__main__":
    main()
