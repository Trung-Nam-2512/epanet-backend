#!/usr/bin/env python3
"""
Script để test frontend có nhận được dữ liệu simulation không
"""

import requests
import json

# API Configuration
API_BASE_URL = "http://localhost:8000"

def test_frontend_data_flow():
    """Test toàn bộ luồng dữ liệu từ API đến frontend"""
    print("Testing Frontend Data Flow")
    print("=" * 50)
    
    # Step 1: Test Network Topology
    print("Step 1: Getting Network Topology...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/network/topology")
        if response.status_code == 200:
            topology_data = response.json()
            nodes = topology_data.get('data', {}).get('nodes', [])
            pipes = topology_data.get('data', {}).get('pipes', [])
            print(f"OK Network Topology: {len(nodes)} nodes, {len(pipes)} pipes")
            
            # Show sample node IDs
            node_ids = [node['id'] for node in nodes[:10]]
            print(f"   Sample Node IDs: {node_ids}")
        else:
            print(f"FAILED Network Topology: {response.status_code}")
            return False
    except Exception as e:
        print(f"ERROR Network Topology: {e}")
        return False
    
    # Step 2: Test Simulation
    print("\nStep 2: Running Simulation...")
    try:
        params = {
            "station_codes": ["13085"],
            "hours_back": 24,
            "duration": 24,
            "hydraulic_timestep": 1,
            "report_timestep": 1
        }
        
        response = requests.post(
            f"{API_BASE_URL}/api/v1/scada/simulation-with-realtime",
            json=params,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            sim_data = response.json()
            print(f"OK Simulation: {sim_data.get('success', False)}")
            
            if sim_data.get('simulation_result'):
                sim_result = sim_data['simulation_result']
                nodes_results = sim_result.get('nodes_results', {})
                pipes_results = sim_result.get('pipes_results', {})
                
                print(f"   Nodes Results: {len(nodes_results)} nodes")
                print(f"   Pipes Results: {len(pipes_results)} pipes")
                
                # Check if frontend node IDs exist in simulation results
                matching_nodes = []
                for node_id in node_ids:
                    if node_id in nodes_results:
                        matching_nodes.append(node_id)
                        node_data = nodes_results[node_id][0] if nodes_results[node_id] else None
                        if node_data:
                            print(f"   Node {node_id}: pressure={node_data.get('pressure', 0):.2f}, flow={node_data.get('flow', 0):.2f}")
                
                print(f"   Matching Nodes: {len(matching_nodes)}/{len(node_ids)}")
                
                if len(matching_nodes) > 0:
                    print("SUCCESS: Frontend should be able to update colors and tooltips!")
                    return True
                else:
                    print("FAILED: No matching nodes found - frontend won't update")
                    return False
            else:
                print("FAILED: No simulation_result in response")
                return False
        else:
            print(f"FAILED Simulation: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"ERROR Simulation: {e}")
        return False

def main():
    """Main test function"""
    success = test_frontend_data_flow()
    
    print("\n" + "=" * 50)
    if success:
        print("SUCCESS: Frontend should work correctly!")
        print("\nNext steps:")
        print("1. Open frontend in browser")
        print("2. Run simulation with station code '13085'")
        print("3. Check if nodes change colors")
        print("4. Click on nodes to see tooltips")
    else:
        print("FAILED: Frontend won't work correctly")
        print("\nIssues to fix:")
        print("1. Check API endpoints")
        print("2. Verify data structure")
        print("3. Check frontend data processing logic")

if __name__ == "__main__":
    main()
