#!/usr/bin/env python3
"""
Script để test tooltip functionality với frontend
"""

import requests
import json
import time

def test_frontend_tooltip():
    """Test tooltip với frontend"""
    print("Testing Frontend Tooltip")
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
        print("1. Testing simulation API...")
        response = requests.post(
            "http://localhost:8000/api/v1/scada/simulation-with-realtime",
            json=params,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            sim_result = data['simulation_result']
            pipes_results = sim_result.get('pipes_results', {})
            
            print(f"   SUCCESS: Got {len(pipes_results)} pipes results")
            
            # Test network topology
            print("2. Testing network topology API...")
            topo_response = requests.get("http://localhost:8000/api/v1/network/topology")
            
            if topo_response.status_code == 200:
                topo_data = topo_response.json()
                pipes = topo_data.get('data', {}).get('pipes', [])
                
                print(f"   SUCCESS: Got {len(pipes)} network pipes")
                
                # Test frontend
                print("3. Testing frontend...")
                frontend_response = requests.get("http://localhost:3000")
                
                if frontend_response.status_code == 200:
                    print("   SUCCESS: Frontend is running")
                    
                    # Show sample data for manual testing
                    print("\n4. Sample data for manual testing:")
                    
                    # Find a pipe with good flow data
                    sample_pipe = None
                    for pipe in pipes[:10]:  # Check first 10 pipes
                        pipe_id = pipe['id']
                        if pipe_id in pipes_results:
                            pipe_data = pipes_results[pipe_id]
                            if pipe_data and len(pipe_data) > 0:
                                latest = pipe_data[-1]
                                flow = latest.get('flow', 0)
                                if abs(flow) > 0.01:  # Find pipe with significant flow
                                    sample_pipe = {
                                        'id': pipe_id,
                                        'from_node': pipe['from_node'],
                                        'to_node': pipe['to_node'],
                                        'flow': flow,
                                        'length': pipe['length'],
                                        'diameter': pipe['diameter']
                                    }
                                    break
                    
                    if sample_pipe:
                        print(f"   Sample pipe for testing: {sample_pipe['id']}")
                        print(f"   - From: {sample_pipe['from_node']}")
                        print(f"   - To: {sample_pipe['to_node']}")
                        print(f"   - Flow: {sample_pipe['flow']:.4f} LPS")
                        print(f"   - Length: {sample_pipe['length']} m")
                        print(f"   - Diameter: {sample_pipe['diameter']} mm")
                        
                        print(f"\n5. Manual testing steps:")
                        print(f"   1. Open browser: http://localhost:3000")
                        print(f"   2. Run simulation with station code: 13085")
                        print(f"   3. Wait for simulation to complete")
                        print(f"   4. Click on pipe: {sample_pipe['id']}")
                        print(f"   5. Check if tooltip shows:")
                        print(f"      - Pipe: {sample_pipe['id']}")
                        print(f"      - From: {sample_pipe['from_node']}")
                        print(f"      - To: {sample_pipe['to_node']}")
                        print(f"      - Flow: {sample_pipe['flow']:.4f} LPS")
                        print(f"   6. Check browser console for debug logs")
                        
                        return True
                    else:
                        print("   ERROR: No pipes with significant flow found")
                        return False
                else:
                    print(f"   ERROR: Frontend not accessible: {frontend_response.status_code}")
                    return False
            else:
                print(f"   ERROR: Network topology API failed: {topo_response.status_code}")
                return False
        else:
            print(f"   ERROR: Simulation API failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ERROR: Exception: {e}")
        return False

def main():
    """Main test function"""
    success = test_frontend_tooltip()
    
    print("\n" + "=" * 50)
    if success:
        print("SUCCESS: All APIs working, ready for manual testing!")
        print("\nNext steps:")
        print("1. Open browser: http://localhost:3000")
        print("2. Run simulation")
        print("3. Click on pipes to test tooltips")
        print("4. Check browser console for debug logs")
    else:
        print("ERROR: Some APIs not working")
        print("\nIssues to fix:")
        print("1. Check backend API status")
        print("2. Check frontend status")
        print("3. Verify data structure")

if __name__ == "__main__":
    main()
