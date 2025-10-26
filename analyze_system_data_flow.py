#!/usr/bin/env python3
"""
Phân tích dữ liệu đầu vào và đầu ra của hệ thống EPANET
"""

import requests
import json

def analyze_system_data_flow():
    """Phân tích flow dữ liệu trong hệ thống"""
    print("=" * 80)
    print("PHAN TICH DU LIEU DAU VAO VA DAU RA CUA HE THONG")
    print("=" * 80)
    
    print("\n1. DU LIEU DAU VAO:")
    print("-" * 50)
    
    # Test SCADA data
    print("Testing SCADA data...")
    try:
        scada_response = requests.get("http://localhost:8000/api/v1/scada/data?station_codes=13085&hours_back=24")
        if scada_response.status_code == 200:
            scada_data = scada_response.json()
            print(f"SCADA API Status: SUCCESS")
            
            if scada_data.get('success') and scada_data.get('data'):
                stations_data = scada_data['data']
                print(f"Number of stations: {len(stations_data)}")
                
                for station_code, station_data in stations_data.items():
                    print(f"\nStation {station_code}:")
                    if station_data.get('records'):
                        latest_record = station_data['records'][-1] if station_data['records'] else {}
                        print(f"  - Pressure: {latest_record.get('pressure', 'N/A')} m")
                        print(f"  - Flow: {latest_record.get('flow', 'N/A')} LPS")
                        print(f"  - Head: {latest_record.get('head', 'N/A')} m")
                        print(f"  - Timestamp: {latest_record.get('timestamp', 'N/A')}")
                    else:
                        print(f"  - No records available")
            else:
                print("No SCADA data available")
        else:
            print(f"SCADA API failed: {scada_response.status_code}")
    except Exception as e:
        print(f"SCADA API error: {e}")
    
    print("\n2. DU LIEU DAU RA:")
    print("-" * 50)
    
    # Test simulation with SCADA data
    print("Testing simulation with SCADA data...")
    try:
        simulation_params = {
            "station_codes": ["13085"],
            "hours_back": 24,
            "duration": 24,
            "hydraulic_timestep": 1,
            "report_timestep": 1
        }
        
        sim_response = requests.post(
            "http://localhost:8000/api/v1/scada/simulation-with-realtime",
            json=simulation_params,
            headers={"Content-Type": "application/json"}
        )
        
        if sim_response.status_code == 200:
            sim_data = sim_response.json()
            print(f"Simulation API Status: SUCCESS")
            
            if sim_data.get('success') and sim_data.get('simulation_result'):
                sim_result = sim_data['simulation_result']
                nodes_results = sim_result.get('nodes_results', {})
                pipes_results = sim_result.get('pipes_results', {})
                
                print(f"Simulation Results:")
                print(f"  - Nodes processed: {len(nodes_results)}")
                print(f"  - Pipes processed: {len(pipes_results)}")
                
                # Check node 2 (main station)
                if '2' in nodes_results:
                    node2_data = nodes_results['2']
                    if node2_data and len(node2_data) > 0:
                        latest_data = node2_data[-1]
                        print(f"\nNode 2 (Main Station) Results:")
                        print(f"  - Demand: {latest_data.get('demand', 0):.5f} LPS")
                        print(f"  - Pressure: {latest_data.get('pressure', 0):.2f} m")
                        print(f"  - Head: {latest_data.get('head', 0):.2f} m")
                        print(f"  - Flow: {latest_data.get('flow', 0):.5f} LPS")
                        print(f"  - Timestamp: {latest_data.get('timestamp', 'N/A')}")
                
                # Check a few other nodes
                sample_nodes = ['3', '31', '43']
                for node_id in sample_nodes:
                    if node_id in nodes_results:
                        node_data = nodes_results[node_id]
                        if node_data and len(node_data) > 0:
                            latest_data = node_data[-1]
                            print(f"\nNode {node_id} Results:")
                            print(f"  - Demand: {latest_data.get('demand', 0):.5f} LPS")
                            print(f"  - Pressure: {latest_data.get('pressure', 0):.2f} m")
                            print(f"  - Head: {latest_data.get('head', 0):.2f} m")
                            print(f"  - Flow: {latest_data.get('flow', 0):.5f} LPS")
                
                # Check pipes
                sample_pipes = list(pipes_results.keys())[:3]
                for pipe_id in sample_pipes:
                    pipe_data = pipes_results[pipe_id]
                    if pipe_data and len(pipe_data) > 0:
                        latest_data = pipe_data[-1]
                        print(f"\nPipe {pipe_id} Results:")
                        print(f"  - Flow: {latest_data.get('flow', 0):.5f} LPS")
                        print(f"  - Velocity: {latest_data.get('velocity', 0):.3f} m/s")
                        print(f"  - Headloss: {latest_data.get('headloss', 0):.3f} m")
            else:
                print("No simulation results available")
        else:
            print(f"Simulation API failed: {sim_response.status_code}")
    except Exception as e:
        print(f"Simulation API error: {e}")
    
    print("\n3. PHAN TICH LOGIC:")
    print("-" * 50)
    
    print("DU LIEU DAU VAO:")
    print("  - SCADA Pressure: Ap luc thuc te tu tram")
    print("  - SCADA Flow: Luu luong thuc te tu tram")
    print("  - Network Topology: Cau truc mang luoi tu file .inp")
    print("  - Fixed Demand: Nhu cau nuoc co dinh tu file .inp")
    
    print("\nDU LIEU DAU RA:")
    print("  - Node Pressure: Ap luc tai cac nut (tinh toan)")
    print("  - Node Head: Cot ap tai cac nut (tinh toan)")
    print("  - Node Flow: Luu luong tai cac nut (tinh toan)")
    print("  - Pipe Flow: Luu luong trong cac ong (tinh toan)")
    print("  - Pipe Velocity: Van toc trong cac ong (tinh toan)")
    print("  - Pipe Headloss: Ton that ap luc trong cac ong (tinh toan)")
    
    print("\n4. LOGIC TINH TOAN:")
    print("-" * 50)
    
    print("EPANET Simulation Process:")
    print("  1. Load network topology from .inp file")
    print("  2. Apply fixed demand to all nodes")
    print("  3. Apply SCADA pressure as boundary condition")
    print("  4. Run hydraulic simulation")
    print("  5. Calculate pressure, head, flow for all nodes/pipes")
    
    print("\nBoundary Conditions:")
    print("  - SCADA Pressure: Applied to specific nodes (e.g., node 2)")
    print("  - Fixed Demand: Applied to all demand nodes")
    print("  - Network Constraints: Pipe diameters, lengths, roughness")
    
    print("\n5. KET QUA MONG DOI:")
    print("-" * 50)
    
    print("Voi du lieu dau vao:")
    print("  - SCADA Pressure: ~8-10 m")
    print("  - SCADA Flow: ~0.05 LPS")
    print("  - Fixed Demand: 0.04872 LPS (node 2)")
    
    print("\nDu lieu dau ra hop ly:")
    print("  - Node 2 Pressure: Gan voi SCADA pressure")
    print("  - Node 2 Flow: Gan voi SCADA flow")
    print("  - Other Nodes Pressure: Tinh toan theo mang luoi")
    print("  - Pipe Flows: Tinh toan theo luu luong")
    
    return True

def main():
    """Main function"""
    try:
        analyze_system_data_flow()
        
        print("\n" + "=" * 80)
        print("KET LUAN:")
        print("=" * 80)
        print("He thong EPANET su dung:")
        print("- SCADA data lam boundary conditions")
        print("- Fixed demand lam input cho simulation")
        print("- Tinh toan pressure, head, flow cho toan bo mang luoi")
        print("- Ket qua la ap luc va luu luong tai tat ca cac nut va ong")
        
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    main()
