#!/usr/bin/env python3
"""
Script để chạy EPANET API
"""
import uvicorn
import os
import sys
from pathlib import Path

def check_requirements():
    """Kiểm tra các yêu cầu cần thiết"""
    print("🔍 Kiểm tra yêu cầu...")
    
    # Kiểm tra file epanet.inp
    if not os.path.exists("epanetVip1.inp"):
        print("❌ Không tìm thấy file epanetVip1.inp")
        print("   Vui lòng đảm bảo file epanetVip1.inp có trong thư mục gốc")
        return False
    
    # Kiểm tra thư mục logs
    os.makedirs("logs", exist_ok=True)
    
    # Kiểm tra thư mục data
    os.makedirs("data", exist_ok=True)
    
    # Kiểm tra thư mục results
    os.makedirs("results", exist_ok=True)
    
    print("✅ Tất cả yêu cầu đã được đáp ứng")
    return True

def main():
    """Hàm chính"""
    print("🚀 Khởi động EPANET Water Network Simulation API")
    print("=" * 60)
    
    # Kiểm tra yêu cầu
    if not check_requirements():
        sys.exit(1)
    
    # Cấu hình server
    host = "0.0.0.0"
    port = 8000
    reload = True
    
    print(f"🌐 Server: http://{host}:{port}")
    print(f"📚 API Docs: http://{host}:{port}/docs")
    print(f"🔄 Reload: {'On' if reload else 'Off'}")
    print("=" * 60)
    
    try:
        # Chạy server
        uvicorn.run(
            "main:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n🛑 Dừng server...")
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
