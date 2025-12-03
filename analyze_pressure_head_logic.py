#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phan tich logic pressure -> head conversion
"""

print("=" * 80)
print("PHAN TICH LOGIC PRESSURE -> HEAD")
print("=" * 80)
print()

print("1. DU LIEU TU SCADA:")
print("   - P1 (Ap luc vao) = 19.24m")
print("   - Q1 (Luu luong thuan) = 44.0 m3/h")
print("   - Don vi: m (cho pressure)")
print()

print("2. TRONG EPANET:")
print("   - Reservoir TXU2: Head = 5.0m (trong file .inp)")
print("   - Coordinates: 106.61, 10.88 (longitude, latitude - KHONG PHAI elevation!)")
print()

print("3. VAN DE:")
print("   - SCADA P1 = 19.24m la GAUGE PRESSURE (ap luc do duoc)")
print("   - De co ABSOLUTE HEAD cho EPANET: Head = Elevation + Gauge Pressure")
print("   - Nhung ELEVATION cua diem do SCADA la bao nhieu?")
print("   - Va ELEVATION cua reservoir TXU2 trong EPANET la bao nhieu?")
print()

print("4. LOGIC HIEN TAI (SAI):")
print("   - Config: elevation = 106.61 (SAI - day la longitude, khong phai elevation!)")
print("   - Head = 106.61 + 19.24 = 125.85m (SAI!)")
print()

print("5. LOGIC DUNG:")
print("   A. Neu SCADA P1 la GAUGE PRESSURE:")
print("      - Can biet elevation cua diem do SCADA (tram 13085)")
print("      - Hoac elevation cua reservoir TXU2 trong EPANET")
print("      - Head = Elevation + P1")
print()
print("   B. Neu SCADA P1 la ABSOLUTE HEAD (da bao gom elevation):")
print("      - Head = P1 = 19.24m (dung truc tiep)")
print()
print("   C. Neu khong biet elevation:")
print("      - Co the su dung base_head tu INP file (5.0m) nhung khong dung SCADA")
print("      - Hoac tim elevation tu coordinates hoac database khac")
print()

print("6. KHUYEN NGHI:")
print("   - Xac dinh elevation cua tram SCADA 13085")
print("   - Hoac xac dinh elevation cua reservoir TXU2 trong EPANET")
print("   - Neu SCADA P1 la absolute head -> dung truc tiep")
print("   - Neu SCADA P1 la gauge pressure -> can cong elevation")
print()


