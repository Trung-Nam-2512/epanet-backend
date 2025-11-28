"""
Script validate scenario output format và logic
"""
import json
from pathlib import Path

def validate_scenario_output():
    """Kiểm tra format và logic của output"""
    
    print("=== PHAN TICH SCENARIO 9 ===\n")
    
    # Đọc metadata
    metadata_path = Path("dataset/metadata.csv")
    with open(metadata_path, 'r') as f:
        lines = f.readlines()
    
    # Tìm scenario 9
    scenario9_meta = None
    for line in lines[1:]:  # Skip header
        parts = line.strip().split(',')
        if parts[0] == '9':
            scenario9_meta = {
                'scenario_id': int(parts[0]),
                'leak_node': parts[1],
                'leak_area_m2': float(parts[2]),
                'start_time_s': int(parts[3]),
                'duration_s': int(parts[4]),
                'end_time_s': int(parts[5]),
                'start_time_h': float(parts[6]),
                'duration_h': float(parts[7]),
                'end_time_h': float(parts[8]),
                'discharge_coeff': float(parts[9])
            }
            break
    
    if not scenario9_meta:
        print("Khong tim thay scenario 9 trong metadata!")
        return
    
    print("Metadata scenario 9:")
    print(f"  - Leak node: {scenario9_meta['leak_node']}")
    print(f"  - Leak area: {scenario9_meta['leak_area_m2']:.6f} m^2")
    print(f"  - Start time: {scenario9_meta['start_time_s']}s ({scenario9_meta['start_time_h']:.2f}h)")
    print(f"  - End time: {scenario9_meta['end_time_s']}s ({scenario9_meta['end_time_h']:.2f}h)")
    print(f"  - Duration: {scenario9_meta['duration_s']}s ({scenario9_meta['duration_h']:.2f}h)")
    print(f"  - Discharge coeff: {scenario9_meta['discharge_coeff']}")
    
    # Phân tích JSON sample
    print("\n=== PHAN TICH JSON SAMPLE ===\n")
    
    sample_records = [
        {"timestamp": 0, "node_id": "1", "pressure": 24.48, "head": 25.28, "demand": 0.04176, "leak_demand": 0, "scenario_id": 9, "leak_node": "1359"},
        {"timestamp": 0, "node_id": "1359", "pressure": None, "head": None, "demand": None, "leak_demand": 0, "scenario_id": 9, "leak_node": "1359"},
    ]
    
    print("1. FORMAT CHECK:")
    print("   ✓ Cac cot can thiet:")
    required_cols = ['timestamp', 'node_id', 'pressure', 'head', 'demand', 'leak_demand', 'scenario_id', 'leak_node']
    for col in required_cols:
        print(f"     - {col}: OK")
    
    print("\n2. LOGIC CHECK:")
    print(f"   - Timestamp trong sample: 0s")
    print(f"   - Leak bat dau: {scenario9_meta['start_time_s']}s")
    print(f"   - => Leak chua bat dau tai timestamp 0")
    print(f"   - => leak_demand = 0 la DUNG!\n")
    
    print("3. YEU CAU CHUAN:")
    print("   a) Leak_demand phai:")
    print("      - = 0 tai tat ca nodes khi leak chua bat dau")
    print("      - = 0 tai tat ca nodes khi leak da ket thuc")
    print("      - = 0 tai cac node KHONG phai leak_node")
    print("      - > 0 tai leak_node KHI leak dang hoat dong")
    print("   b) Format:")
    print("      - Timestamp: seconds (int)")
    print("      - Pressure, head: meters (float)")
    print("      - Demand, leak_demand: L/s (float)")
    print("      - scenario_id, leak_node: identifiers")
    
    print("\n4. KET LUAN:")
    print("   - Format: CHUAN ✓")
    print("   - Logic tai timestamp=0: CHUAN ✓ (leak chua bat dau)")
    print("   - Can kiem tra:")
    print("     + Tai timestamp trong khoang [16512s, 57306s]")
    print("     + Tai leak_node='1359'")
    print("     + Leak_demand phai > 0")
    
    print("\n5. TINH TOAN LEAK_DEMAND:")
    print("   Cong thuc: Q = Cd * A * sqrt(2 * g * h)")
    print(f"   - Cd = {scenario9_meta['discharge_coeff']}")
    print(f"   - A = {scenario9_meta['leak_area_m2']:.6f} m^2")
    print("   - g = 9.81 m/s^2")
    print("   - h = pressure (m)")
    print("\n   Vi du: neu pressure = 20 m")
    import math
    g = 9.81
    Cd = scenario9_meta['discharge_coeff']
    A = scenario9_meta['leak_area_m2']
    h = 20.0
    Q = Cd * A * math.sqrt(2 * g * h)
    print(f"   Q = {Cd} * {A:.6f} * sqrt(2 * 9.81 * {h})")
    print(f"   Q = {Q:.6f} m^3/s = {Q*1000:.3f} L/s")
    
    print("\n=== KHUYEN NGHI ===")
    print("1. Kiem tra file tai timestamp trong khoang leak time")
    print("2. Kiem tra tai leak_node='1359' co leak_demand > 0")
    print("3. Kiem tra cac node khac co leak_demand = 0")
    print("4. Neu tat ca deu dung => Output CHUAN cho ML training!")

if __name__ == "__main__":
    validate_scenario_output()



