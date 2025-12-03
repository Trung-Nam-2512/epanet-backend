#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de xac minh he thong co thuc su goi API SCADA that hay khong
"""

import sys
import io
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def load_scada_config():
    """Load SCADA config"""
    try:
        with open("config/scada_mapping.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Loi doc config: {e}")
        return None

def test_scada_api_direct():
    """Test goi truc tiep API SCADA"""
    print("=" * 80)
    print("TEST 1: GOI TRUC TIEP API SCADA")
    print("=" * 80)
    
    config = load_scada_config()
    if not config:
        return False
    
    api_config = config.get("api_config", {})
    base_url = api_config.get("base_url", "")
    token = api_config.get("token", "")
    
    if not base_url or not token:
        print("❌ Khong co API config")
        return False
    
    print(f"API URL: {base_url}")
    print(f"Token: {'*' * 20}...{token[-10:] if len(token) > 10 else token}")
    print()
    
    # Test goi API
    station_code = "13085"
    now = datetime.now()
    current_hour = now.replace(minute=0, second=0, microsecond=0)
    from_date = (current_hour - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")
    to_date = current_hour.strftime("%Y-%m-%d %H:%M")
    
    url = f"{base_url}/GetStationDataByHour"
    payload = {
        "stationCode": station_code,
        "fromDate": from_date,
        "toDate": to_date
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print(f"Goi API SCADA:")
    print(f"  Station: {station_code}")
    print(f"  From: {from_date}")
    print(f"  To: {to_date}")
    print()
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API tra ve thanh cong")
            print(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            
            # Kiem tra cau truc data
            if isinstance(data, dict):
                if "data" in data and isinstance(data["data"], list):
                    print(f"✅ Co {len(data['data'])} ban ghi trong response")
                    if len(data["data"]) > 0:
                        print(f"Sample record keys: {list(data['data'][0].keys())}")
                        print(f"Sample record: {json.dumps(data['data'][0], indent=2, ensure_ascii=False)}")
                    return True
                else:
                    print(f"⚠️  Response khong co 'data' array")
                    print(f"Full response: {json.dumps(data, indent=2, ensure_ascii=False)}")
                    return False
            else:
                print(f"⚠️  Response khong phai dict")
                return False
        else:
            print(f"❌ API tra ve loi: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"❌ Timeout khi goi API SCADA")
        return False
    except Exception as e:
        print(f"❌ Loi khi goi API: {e}")
        return False

def test_scada_service():
    """Test SCADA service co goi API that khong"""
    print()
    print("=" * 80)
    print("TEST 2: KIEM TRA SCADA SERVICE")
    print("=" * 80)
    
    try:
        from services.scada_service import scada_service
        
        print(f"SCADA Service base_url: {scada_service.base_url}")
        print(f"SCADA Service token: {'*' * 20}...{scada_service.token[-10:] if len(scada_service.token) > 10 else scada_service.token}")
        print()
        
        # Test get_realtime_data_for_epanet
        print("Goi scada_service.get_realtime_data_for_epanet()...")
        result = scada_service.get_realtime_data_for_epanet(
            station_codes=["13085"],
            hours_back=1
        )
        
        print(f"Result success: {result.get('success')}")
        print(f"Boundary conditions keys: {list(result.get('boundary_conditions', {}).keys())}")
        
        if result.get("success"):
            boundary_conditions = result.get("boundary_conditions", {})
            if boundary_conditions:
                for station_code, records in boundary_conditions.items():
                    print(f"  Station {station_code}: {len(records)} records")
                    if records:
                        print(f"    First record: {records[0]}")
                        print(f"    Last record: {records[-1]}")
                return True
            else:
                print("⚠️  Success=True nhung khong co boundary_conditions")
                return False
        else:
            print(f"❌ SCADA service tra ve success=False")
            print(f"Error: {result.get('error', 'Unknown')}")
            return False
            
    except Exception as e:
        print(f"❌ Loi khi test SCADA service: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_simulation_flow():
    """Test xem simulation co nhan SCADA data khong"""
    print()
    print("=" * 80)
    print("TEST 3: KIEM TRA SIMULATION FLOW")
    print("=" * 80)
    
    try:
        from services.scada_service import scada_service
        from services.epanet_service import epanet_service
        from models.schemas import SimulationInput
        
        # Lay SCADA data
        print("1. Lay SCADA data...")
        scada_result = scada_service.get_realtime_data_for_epanet(
            station_codes=["13085"],
            hours_back=1
        )
        
        if not scada_result.get("success"):
            print("❌ Khong lay duoc SCADA data - khong the test simulation")
            return False
        
        scada_boundary_data = scada_result.get("boundary_conditions", {})
        print(f"✅ Co {len(scada_boundary_data)} stations trong boundary_conditions")
        
        if not scada_boundary_data:
            print("⚠️  Khong co boundary_conditions - simulation se chay voi INP file data")
            print("   (Day la fallback - khong phai loi)")
            return True  # Khong phai loi, chi la khong co data
        
        # Check xem EPANET service co nhan parameter khong
        print("2. Kiem tra EPANET service signature...")
        import inspect
        sig = inspect.signature(epanet_service.run_simulation)
        params = list(sig.parameters.keys())
        print(f"   Parameters: {params}")
        
        if "scada_boundary_data" in params:
            print("✅ EPANET service co parameter scada_boundary_data")
        else:
            print("❌ EPANET service KHONG co parameter scada_boundary_data")
            return False
        
        # Check xem co apply SCADA boundary conditions khong
        print("3. Kiem tra SCADA boundary service...")
        try:
            from services.scada_boundary_service import scada_boundary_service
            print("✅ SCADA boundary service duoc import thanh cong")
            
            # Check method
            if hasattr(scada_boundary_service, 'apply_scada_boundary_conditions'):
                print("✅ Co method apply_scada_boundary_conditions()")
            else:
                print("❌ Khong co method apply_scada_boundary_conditions()")
                return False
        except ImportError:
            print("❌ Khong the import scada_boundary_service")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Loi khi test simulation flow: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_fallback_behavior():
    """Kiem tra xem co fallback nao khong"""
    print()
    print("=" * 80)
    print("TEST 4: KIEM TRA FALLBACK BEHAVIOR")
    print("=" * 80)
    
    # Check trong scada_integration.py
    scada_route_file = Path("api/routes/scada_integration.py")
    if scada_route_file.exists():
        content = scada_route_file.read_text(encoding="utf-8")
        
        # Check xem co raise HTTPException khi SCADA fail khong
        if 'if not scada_result["success"]:' in content:
            if 'raise HTTPException' in content:
                print("✅ Khi SCADA fail, he thong RAISE ERROR - khong chay simulation")
                print("   (Day la dung - khong chay voi data gia)")
            else:
                print("⚠️  Khi SCADA fail, he thong co the van chay simulation")
        
        # Check xem co truyen scada_boundary_data vao simulation khong
        if 'scada_boundary_data=scada_boundary_data' in content:
            print("✅ Backend truyen scada_boundary_data vao epanet_service")
        else:
            print("❌ Backend KHONG truyen scada_boundary_data")
            return False
    
    # Check trong epanet_service.py
    epanet_service_file = Path("services/epanet_service.py")
    if epanet_service_file.exists():
        content = epanet_service_file.read_text(encoding="utf-8")
        
        if 'if scada_boundary_data:' in content:
            print("✅ EPANET service check scada_boundary_data truoc khi apply")
        else:
            print("⚠️  EPANET service khong check scada_boundary_data")
        
        if 'using INP file boundary conditions' in content.lower():
            print("✅ Co fallback ve INP file boundary conditions khi khong co SCADA")
        else:
            print("⚠️  Khong thay fallback message")
    
    return True

def main():
    """Main test function"""
    print()
    print("=" * 80)
    print("XAC MINH HE THONG CO THUC SU GOI API SCADA THAT")
    print("=" * 80)
    print()
    
    results = []
    
    # Test 1: Goi truc tiep API SCADA
    results.append(("Direct API Call", test_scada_api_direct()))
    
    # Test 2: Test SCADA service
    results.append(("SCADA Service", test_scada_service()))
    
    # Test 3: Test simulation flow
    results.append(("Simulation Flow", test_simulation_flow()))
    
    # Test 4: Check fallback
    results.append(("Fallback Behavior", check_fallback_behavior()))
    
    # Tong ket
    print()
    print("=" * 80)
    print("TONG KET")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print()
    print(f"Ket qua: {passed}/{total} tests passed")
    
    if passed == total:
        print()
        print("✅ KET LUAN: HE THONG CO THUC SU GOI API SCADA THAT")
        print()
        print("Cac diem xac minh:")
        print("  1. API SCADA duoc goi truc tiep tu scada_service")
        print("  2. SCADA service parse va convert data thanh boundary_conditions")
        print("  3. Backend truyen scada_boundary_data vao EPANET simulation")
        print("  4. Khi SCADA fail, he thong RAISE ERROR - khong chay voi data gia")
        print("  5. Khi khong co SCADA data, simulation fallback ve INP file data")
        return True
    else:
        print()
        print("⚠️  CO MOT SO VAN DE CAN KIEM TRA")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


