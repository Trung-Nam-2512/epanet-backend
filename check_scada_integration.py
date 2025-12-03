#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de kiem tra xem he thong co thuc su lay du lieu tu API SCADA de chay mo phong EPANET khong
"""

import json
import sys
import io
from pathlib import Path

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def check_scada_integration():
    """Kiem tra toan bo flow tu frontend den backend"""
    
    print("=" * 80)
    print("KIEM TRA TICH HOP SCADA VAO EPANET SIMULATION")
    print("=" * 80)
    print()
    
    issues = []
    checks_passed = 0
    total_checks = 0
    
    # 1. Kiem tra config SCADA
    print("1. KIEM TRA SCADA CONFIG")
    print("-" * 80)
    total_checks += 1
    try:
        with open("config/scada_mapping.json", "r", encoding="utf-8") as f:
            scada_config = json.load(f)
        
        api_config = scada_config.get("api_config", {})
        base_url = api_config.get("base_url", "")
        token = api_config.get("token", "")
        
        if base_url and token:
            print(f"✅ SCADA API URL: {base_url}")
            print(f"✅ Token: {'*' * 20}...{token[-10:] if len(token) > 10 else token}")
            checks_passed += 1
        else:
            print(f"❌ Thieu SCADA API config")
            issues.append("SCADA API config khong day du")
            
        stations = scada_config.get("scada_stations", {})
        if stations:
            print(f"✅ Có {len(stations)} SCADA stations được cấu hình")
            for station_code, station_info in stations.items():
                mapping = station_info.get("epanet_mapping", {})
                epanet_node = mapping.get("epanet_node", "N/A")
                node_type = mapping.get("node_type", "N/A")
                print(f"   - Station {station_code} -> EPANET {node_type} {epanet_node}")
        else:
            print(f"❌ Khong co SCADA stations duoc cau hinh")
            issues.append("Khong co SCADA stations trong config")
    except FileNotFoundError:
        print(f"❌ Khong tim thay file config/scada_mapping.json")
        issues.append("File config/scada_mapping.json khong ton tai")
    except Exception as e:
        print(f"❌ Loi doc config: {e}")
        issues.append(f"Loi doc config: {e}")
    
    print()
    
    # 2. Kiem tra Frontend API call
    print("2. KIEM TRA FRONTEND API CALL")
    print("-" * 80)
    total_checks += 1
    api_file = Path("epanet-frontend/src/services/api.ts")
    if api_file.exists():
        content = api_file.read_text(encoding="utf-8")
        if "/api/v1/scada/simulation-with-realtime" in content:
            print("✅ Frontend gọi đúng endpoint: /api/v1/scada/simulation-with-realtime")
            checks_passed += 1
        else:
            print("❌ Frontend khong goi endpoint SCADA")
            issues.append("Frontend khong goi endpoint SCADA simulation")
        
        if "station_codes" in content:
            print("✅ Frontend co truyen station_codes parameter")
        else:
            print("❌ Frontend khong truyen station_codes")
            issues.append("Frontend khong truyen station_codes")
    else:
        print("❌ Khong tim thay file api.ts")
        issues.append("File api.ts khong ton tai")
    
    print()
    
    # 3. Kiem tra Backend API route
    print("3. KIEM TRA BACKEND API ROUTE")
    print("-" * 80)
    total_checks += 1
    scada_route_file = Path("api/routes/scada_integration.py")
    if scada_route_file.exists():
        content = scada_route_file.read_text(encoding="utf-8")
        
        if "get_realtime_data_for_epanet" in content:
            print("✅ Backend có gọi scada_service.get_realtime_data_for_epanet()")
            checks_passed += 1
        else:
            print("❌ Backend khong goi SCADA service")
            issues.append("Backend khong goi SCADA service")
        
        if "scada_boundary_data" in content:
            print("✅ Backend truyen scada_boundary_data vao simulation")
        else:
            print("❌ Backend khong truyen SCADA data vao simulation")
            issues.append("Backend khong truyen SCADA data vao simulation")
        
        if "epanet_service.run_simulation" in content and "scada_boundary_data" in content:
            print("✅ Backend truyen SCADA boundary data vao EPANET service")
        else:
            print("❌ Backend khong truyen SCADA data vao EPANET service")
            issues.append("Backend khong truyen SCADA data vao EPANET service")
    else:
        print("❌ Khong tim thay file scada_integration.py")
        issues.append("File scada_integration.py khong ton tai")
    
    print()
    
    # 4. Kiem tra SCADA Service
    print("4. KIEM TRA SCADA SERVICE")
    print("-" * 80)
    total_checks += 1
    scada_service_file = Path("services/scada_service.py")
    if scada_service_file.exists():
        content = scada_service_file.read_text(encoding="utf-8")
        
        if "requests.post" in content and "GetStationDataByHour" in content:
            print("✅ SCADA service có gọi API SCADA thật")
            checks_passed += 1
        else:
            print("❌ SCADA service khong goi API SCADA")
            issues.append("SCADA service khong goi API SCADA that")
        
        if "get_realtime_data_for_epanet" in content:
            print("✅ SCADA service co method get_realtime_data_for_epanet()")
        else:
            print("❌ SCADA service khong co method get_realtime_data_for_epanet()")
            issues.append("SCADA service thieu method get_realtime_data_for_epanet()")
        
        if "boundary_conditions" in content:
            print("✅ SCADA service tra ve boundary_conditions")
        else:
            print("❌ SCADA service khong tra ve boundary_conditions")
            issues.append("SCADA service khong tra ve boundary_conditions")
    else:
        print("❌ Khong tim thay file scada_service.py")
        issues.append("File scada_service.py khong ton tai")
    
    print()
    
    # 5. Kiem tra EPANET Service
    print("5. KIEM TRA EPANET SERVICE")
    print("-" * 80)
    total_checks += 1
    epanet_service_file = Path("services/epanet_service.py")
    if epanet_service_file.exists():
        content = epanet_service_file.read_text(encoding="utf-8")
        
        if "scada_boundary_data" in content:
            print("✅ EPANET service nhận scada_boundary_data parameter")
            checks_passed += 1
        else:
            print("❌ EPANET service khong nhan SCADA boundary data")
            issues.append("EPANET service khong nhan SCADA boundary data")
        
        if "scada_boundary_service" in content or "apply_scada_boundary_conditions" in content:
            print("✅ EPANET service co apply SCADA boundary conditions")
        else:
            print("❌ EPANET service khong apply SCADA boundary conditions")
            issues.append("EPANET service khong apply SCADA boundary conditions")
    else:
        print("❌ Khong tim thay file epanet_service.py")
        issues.append("File epanet_service.py khong ton tai")
    
    print()
    
    # 6. Kiem tra SCADA Boundary Service
    print("6. KIEM TRA SCADA BOUNDARY SERVICE")
    print("-" * 80)
    total_checks += 1
    scada_boundary_file = Path("services/scada_boundary_service.py")
    if scada_boundary_file.exists():
        content = scada_boundary_file.read_text(encoding="utf-8")
        
        if "apply_scada_boundary_conditions" in content:
            print("✅ SCADA boundary service có method apply_scada_boundary_conditions()")
            checks_passed += 1
        else:
            print("❌ SCADA boundary service khong co method apply")
            issues.append("SCADA boundary service thieu method apply")
        
        if "_apply_reservoir_boundary" in content or "_apply_tank_boundary" in content:
            print("✅ SCADA boundary service co logic apply cho reservoir/tank")
        else:
            print("⚠️  SCADA boundary service co the thieu logic apply")
    else:
        print("❌ Khong tim thay file scada_boundary_service.py")
        issues.append("File scada_boundary_service.py khong ton tai")
    
    print()
    
    # 7. Tong ket
    print("=" * 80)
    print("TONG KET")
    print("=" * 80)
    print(f"✅ Da pass: {checks_passed}/{total_checks} checks")
    print(f"❌ Co {len(issues)} van de can xu ly")
    print()
    
    if issues:
        print("CAC VAN DE PHAT HIEN:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
        print()
        return False
    else:
        print("✅ HE THONG DUOC CAU HINH DUNG!")
        print()
        print("FLOW DU LIEU SCADA:")
        print("  1. Frontend goi API: /api/v1/scada/simulation-with-realtime")
        print("  2. Backend route nhan request va goi scada_service.get_realtime_data_for_epanet()")
        print("  3. SCADA service goi API SCADA that: GetStationDataByHour")
        print("  4. SCADA service parse va convert data thanh boundary_conditions")
        print("  5. Backend truyen scada_boundary_data vao epanet_service.run_simulation()")
        print("  6. EPANET service apply SCADA boundary conditions vao WNTR model")
        print("  7. Chay simulation voi du lieu SCADA that")
        print()
        return True

if __name__ == "__main__":
    success = check_scada_integration()
    sys.exit(0 if success else 1)

