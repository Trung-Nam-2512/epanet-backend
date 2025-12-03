#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de debug head calculation
"""

import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def analyze_head_issue():
    """Phan tich van de head calculation"""
    
    print("=" * 80)
    print("PHAN TICH VAN DE HEAD CALCULATION")
    print("=" * 80)
    print()
    
    print("1. DU LIEU TU FILE .INP:")
    print("   - Reservoir TXU2: Head = 5.0m (trong file .inp)")
    print("   - Reservoir TXU2: Elevation = 106.61m (từ coordinates)")
    print()
    
    print("2. DU LIEU TU SCADA:")
    print("   - Pressure (P1) = 19.3m")
    print("   - Config: pressure_type = 'absolute'")
    print("   - Config: elevation = 0.0")
    print()
    
    print("3. LOGIC HIEN TAI:")
    print("   - pressure_type = 'absolute' → head_value = pressure_value = 19.3m")
    print("   - Code set: node.base_head = 19.3m")
    print()
    
    print("4. VAN DE CO THE:")
    print()
    print("   A. NEU SCADA PRESSURE LA GAUGE (khong phai absolute):")
    print("      - Head = Elevation + Pressure = 106.61 + 19.3 = 125.91m")
    print("      - Nhung config nói 'absolute' nen khong cong elevation")
    print()
    print("   B. NEU SCADA PRESSURE LA ABSOLUTE HEAD:")
    print("      - Head = 19.3m (dung)")
    print("      - Nhung tai sao simulation ra 40m?")
    print()
    print("   C. CO THE CO VAN DE VOI WNTR PATTERN:")
    print("      - Code tạo pattern với multipliers")
    print("      - base_head = simulation_heads[0] = 19.3m")
    print("      - multipliers = [head_val / base_head for head_val in simulation_heads]")
    print("      - Nếu có nhiều giá trị, multipliers có thể làm thay đổi head")
    print()
    print("   D. CO THE DANG DUNG SAI BASE_HEAD:")
    print("      - Code check: if abs(base_head) > 0.001")
    print("      - Nếu base_head từ INP file (5.0m) được dùng thay vì SCADA data")
    print()
    
    print("5. KHUYEN NGHI:")
    print("   - Kiểm tra xem SCADA pressure có phải là absolute head hay gauge pressure")
    print("   - Nếu là gauge pressure → cần cộng elevation")
    print("   - Nếu là absolute head → không cộng elevation")
    print("   - Kiểm tra logs để xem base_head được set là bao nhiêu")
    print("   - Kiểm tra xem có đang dùng pattern multipliers không đúng không")
    print()
    
    # Test calculation
    print("6. TEST CALCULATION:")
    scada_pressure = 19.3
    elevation = 106.61
    inp_base_head = 5.0
    
    print(f"   Scenario 1: SCADA pressure là absolute head")
    print(f"      → head_value = {scada_pressure}m")
    print()
    
    print(f"   Scenario 2: SCADA pressure là gauge pressure")
    print(f"      → head_value = elevation + pressure = {elevation} + {scada_pressure} = {elevation + scada_pressure}m")
    print()
    
    print(f"   Scenario 3: Dùng base_head từ INP file")
    print(f"      → head_value = {inp_base_head}m (SAI - không dùng SCADA data)")
    print()
    
    print(f"   Scenario 4: Cộng base_head từ INP với SCADA pressure")
    print(f"      → head_value = {inp_base_head} + {scada_pressure} = {inp_base_head + scada_pressure}m (SAI)")
    print()

if __name__ == "__main__":
    analyze_head_issue()


