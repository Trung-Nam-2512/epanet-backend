#!/usr/bin/env python3
"""
Script để test tooltip functionality
"""

import requests
import json

def test_tooltip_data():
    """Test dữ liệu cho tooltip"""
    print("Testing Tooltip Data")
    print("=" * 50)
    
    # Test simulation API để lấy dữ liệu pipes
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
        
        if response.status_code == 200:
            data = response.json()
            sim_result = data['simulation_result']
            pipes_results = sim_result.get('pipes_results', {})
            
            print(f"Pipes Results: {len(pipes_results)} pipes")
            
            # Show sample pipe data
            if pipes_results:
                sample_pipe_id = list(pipes_results.keys())[0]
                sample_pipe_data = pipes_results[sample_pipe_id]
                
                print(f"\nSample Pipe Data ({sample_pipe_id}):")
                if sample_pipe_data and len(sample_pipe_data) > 0:
                    latest_data = sample_pipe_data[-1]
                    print(f"- Flow: {latest_data.get('flow', 0):.4f} LPS")
                    print(f"- Timestamp: {latest_data.get('timestamp', 'N/A')}")
                else:
                    print("- No data available")
                
                # Show first 5 pipes
                print(f"\nFirst 5 pipes:")
                for i, (pipe_id, pipe_data) in enumerate(list(pipes_results.items())[:5]):
                    if pipe_data and len(pipe_data) > 0:
                        latest = pipe_data[-1]
                        flow = latest.get('flow', 0)
                        print(f"- {pipe_id}: flow={flow:.4f} LPS")
                    else:
                        print(f"- {pipe_id}: no data")
            
            # Test network topology để lấy pipe properties
            print(f"\nTesting Network Topology...")
            topo_response = requests.get("http://localhost:8000/api/v1/network/topology")
            
            if topo_response.status_code == 200:
                topo_data = topo_response.json()
                pipes = topo_data.get('data', {}).get('pipes', [])
                
                print(f"Network Pipes: {len(pipes)} pipes")
                
                if pipes:
                    sample_pipe = pipes[0]
                    print(f"\nSample Network Pipe:")
                    print(f"- ID: {sample_pipe.get('id')}")
                    print(f"- From: {sample_pipe.get('from_node')}")
                    print(f"- To: {sample_pipe.get('to_node')}")
                    print(f"- Length: {sample_pipe.get('length')}")
                    print(f"- Diameter: {sample_pipe.get('diameter')}")
                    print(f"- Roughness: {sample_pipe.get('roughness')}")
                    print(f"- Status: {sample_pipe.get('status')}")
                
                # Test tooltip data structure
                print(f"\nTooltip Data Structure Test:")
                if pipes and pipes_results:
                    # Find a pipe that exists in both
                    network_pipe_ids = [p['id'] for p in pipes]
                    simulation_pipe_ids = list(pipes_results.keys())
                    
                    common_pipes = set(network_pipe_ids) & set(simulation_pipe_ids)
                    print(f"- Common pipes: {len(common_pipes)}")
                    
                    if common_pipes:
                        test_pipe_id = list(common_pipes)[0]
                        network_pipe = next(p for p in pipes if p['id'] == test_pipe_id)
                        simulation_data = pipes_results[test_pipe_id]
                        
                        if simulation_data and len(simulation_data) > 0:
                            latest_sim = simulation_data[-1]
                            
                            # This is what should be in tooltip properties
                            tooltip_properties = {
                                'id': network_pipe['id'],
                                'from_node': network_pipe['from_node'],
                                'to_node': network_pipe['to_node'],
                                'flow': latest_sim.get('flow', 0),
                                'velocity': 0,  # Not calculated yet
                                'headloss': 0,  # Not calculated yet
                                'length': network_pipe['length'],
                                'diameter': network_pipe['diameter'],
                                'roughness': network_pipe['roughness'],
                                'status': network_pipe['status']
                            }
                            
                            print(f"\nTooltip Properties for {test_pipe_id}:")
                            for key, value in tooltip_properties.items():
                                print(f"- {key}: {value}")
                            
                            print(f"\nTooltip should display:")
                            print(f"- Pipe: {test_pipe_id}")
                            print(f"- From: {tooltip_properties['from_node']}")
                            print(f"- To: {tooltip_properties['to_node']}")
                            print(f"- Flow: {tooltip_properties['flow']:.4f} LPS")
                            print(f"- Length: {tooltip_properties['length']} m")
                            print(f"- Diameter: {tooltip_properties['diameter']} mm")
                            
                            return True
                        else:
                            print(f"ERROR: No simulation data for pipe {test_pipe_id}")
                            return False
                    else:
                        print(f"ERROR: No common pipes between network and simulation")
                        return False
                else:
                    print(f"ERROR: Missing network or simulation data")
                    return False
            else:
                print(f"ERROR: Network topology API failed: {topo_response.status_code}")
                return False
        else:
            print(f"ERROR: Simulation API failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"ERROR: Exception: {e}")
        return False

def main():
    """Main test function"""
    success = test_tooltip_data()
    
    print("\n" + "=" * 50)
    if success:
        print("SUCCESS: Tooltip data structure is correct!")
        print("\nNext steps:")
        print("1. Open frontend in browser")
        print("2. Run simulation")
        print("3. Click on pipes to see tooltips")
        print("4. Check browser console for debug logs")
    else:
        print("ERROR: Tooltip data structure has issues")
        print("\nIssues to fix:")
        print("1. Check API data structure")
        print("2. Verify pipe properties mapping")
        print("3. Check frontend tooltip component")

if __name__ == "__main__":
    main()
