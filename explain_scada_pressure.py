#!/usr/bin/env python3
"""
Giải thích chi tiết về cách SCADA Pressure được áp dụng trong hệ thống EPANET
"""

import requests
import json

def explain_scada_pressure_application():
    """Giải thích cách SCADA Pressure được áp dụng"""
    print("=" * 80)
    print("GIAI THICH CACH SCADA PRESSURE DUOC AP DUNG")
    print("=" * 80)
    
    print("\n1. MAPPING SCADA STATIONS TO EPANET NODES:")
    print("-" * 60)
    
    # Load mapping từ config
    try:
        with open("config/scada_mapping.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        
        station_mapping = config.get("station_mapping", {})
        
        print("SCADA Station -> EPANET Node Mapping:")
        for station_code, station_info in station_mapping.items():
            epanet_node = station_info.get("epanet_node")
            description = station_info.get("description")
            location = station_info.get("location")
            
            print(f"  Station {station_code} -> Node {epanet_node}")
            print(f"    Description: {description}")
            print(f"    Location: {location}")
            print()
            
    except Exception as e:
        print(f"Error loading config: {e}")
    
    print("\n2. CACH SCADA PRESSURE DUOC AP DUNG:")
    print("-" * 60)
    
    print("SCADA Pressure duoc ap dung theo 2 cach:")
    print()
    
    print("A. CHO TANK/RESERVOIR NODES:")
    print("   - Cap nhat 'initial_level' cua tank/reservoir")
    print("   - Ap dung pressure tu SCADA lam muc nuoc ban dau")
    print("   - Vi du: Node 2 (TXU2) - Tank chinh")
    print()
    
    print("B. CHO DEMAND NODES:")
    print("   - Cap nhat 'elevation' cua node")
    print("   - Ap dung pressure tu SCADA lam cot ap")
    print("   - Vi du: Node 3, 31, 43, 64 - Cac diem tieu thu")
    print()
    
    print("3. CAC NODE KHAC KHONG CO SCADA:")
    print("-" * 60)
    
    print("Cac node khong co SCADA data se:")
    print("  - Su dung elevation co dinh tu file .inp")
    print("  - Su dung demand co dinh tu file .inp")
    print("  - Duoc tinh toan ap luc tu simulation")
    print()
    
    print("4. LOGIC TINH TOAN:")
    print("-" * 60)
    
    print("EPANET Simulation Process:")
    print("  1. Load network topology tu file .inp")
    print("  2. Apply SCADA pressure cho cac node co SCADA:")
    print("     - Tank/Reservoir: Set initial_level")
    print("     - Demand nodes: Set elevation")
    print("  3. Apply fixed demand cho tat ca demand nodes")
    print("  4. Run hydraulic simulation")
    print("  5. Calculate pressure cho tat ca nodes")
    print()
    
    print("5. VI DU CU THE:")
    print("-" * 60)
    
    print("Voi SCADA Station 13085 -> Node 2:")
    print("  - SCADA Pressure: 8.5 m")
    print("  - Node 2 la tank (TXU2)")
    print("  - Set initial_level = 8.5 m")
    print("  - Simulation se tinh pressure cho cac node khac")
    print()
    
    print("Voi SCADA Station 13086 -> Node 3:")
    print("  - SCADA Pressure: 7.2 m")
    print("  - Node 3 la demand node")
    print("  - Set elevation = 7.2 m")
    print("  - Simulation se tinh pressure tai node 3")
    print()
    
    print("6. TAI SAO CHI AP DUNG CHO NODE CU THE:")
    print("-" * 60)
    
    print("A. SCADA chi co tai mot so diem do:")
    print("   - Khong the do pressure tai tat ca nodes")
    print("   - Chi co tai cac tram quan trong")
    print("   - Cac node khac duoc tinh toan tu simulation")
    print()
    
    print("B. Boundary Conditions:")
    print("   - SCADA pressure la dieu kien bien")
    print("   - EPANET su dung de tinh toan toan bo mang")
    print("   - Cac node khac duoc tinh tu cac phuong trinh thuy luc")
    print()
    
    print("C. Thuc te van hanh:")
    print("   - Chi co mot so diem do thuc te")
    print("   - Cac diem khac duoc tinh toan")
    print("   - Day la cach hoat dong binh thuong cua he thong")
    print()
    
    print("7. KET QUA CUOI CUNG:")
    print("-" * 60)
    
    print("Sau simulation, tat ca nodes se co:")
    print("  - Pressure: Ap luc tai node")
    print("  - Head: Cot ap tai node")
    print("  - Flow: Luu luong tai node")
    print()
    
    print("Cac node co SCADA:")
    print("  - Pressure gan voi SCADA pressure")
    print("  - Duoc su dung lam boundary condition")
    print()
    
    print("Cac node khong co SCADA:")
    print("  - Pressure duoc tinh tu simulation")
    print("  - Dua tren topology va demand")
    print("  - Duoc tinh tu cac phuong trinh thuy luc")
    
    return True

def test_scada_pressure_application():
    """Test cách SCADA pressure được áp dụng"""
    print("\n" + "=" * 80)
    print("TEST SCADA PRESSURE APPLICATION")
    print("=" * 80)
    
    try:
        # Test simulation với SCADA data
        simulation_params = {
            "station_codes": ["13085", "13086", "13087", "13088", "13089"],
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
            print("Simulation API Status: SUCCESS")
            
            if sim_data.get('success') and sim_data.get('simulation_result'):
                sim_result = sim_data['simulation_result']
                nodes_results = sim_result.get('nodes_results', {})
                
                print(f"\nNodes processed: {len(nodes_results)}")
                
                # Check các node có SCADA
                scada_nodes = ["2", "3", "31", "43", "64"]
                print("\nSCADA Nodes Results:")
                for node_id in scada_nodes:
                    if node_id in nodes_results:
                        node_data = nodes_results[node_id]
                        if node_data and len(node_data) > 0:
                            latest_data = node_data[-1]
                            print(f"\nNode {node_id} (SCADA):")
                            print(f"  - Demand: {latest_data.get('demand', 0):.5f} LPS")
                            print(f"  - Pressure: {latest_data.get('pressure', 0):.2f} m")
                            print(f"  - Head: {latest_data.get('head', 0):.2f} m")
                            print(f"  - Flow: {latest_data.get('flow', 0):.5f} LPS")
                
                # Check một số node không có SCADA
                non_scada_nodes = ["1", "4", "5", "6", "7", "8", "9", "10"]
                print("\nNon-SCADA Nodes Results:")
                for node_id in non_scada_nodes:
                    if node_id in nodes_results:
                        node_data = nodes_results[node_id]
                        if node_data and len(node_data) > 0:
                            latest_data = node_data[-1]
                            print(f"\nNode {node_id} (Non-SCADA):")
                            print(f"  - Demand: {latest_data.get('demand', 0):.5f} LPS")
                            print(f"  - Pressure: {latest_data.get('pressure', 0):.2f} m")
                            print(f"  - Head: {latest_data.get('head', 0):.2f} m")
                            print(f"  - Flow: {latest_data.get('flow', 0):.5f} LPS")
        else:
            print(f"Simulation API failed: {sim_response.status_code}")
            
    except Exception as e:
        print(f"Test error: {e}")

def main():
    """Main function"""
    try:
        explain_scada_pressure_application()
        test_scada_pressure_application()
        
        print("\n" + "=" * 80)
        print("KET LUAN:")
        print("=" * 80)
        print("SCADA Pressure duoc ap dung cho:")
        print("  - Cac node cu the co SCADA station")
        print("  - Lam boundary condition cho simulation")
        print("  - Cac node khac duoc tinh tu simulation")
        print("  - Day la cach hoat dong binh thuong cua he thong")
        
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    main()
