"""
Script để cài đặt EPANET Toolkit
"""
import os
import sys
import platform
import subprocess
import urllib.request
import zipfile
import shutil

def install_wntr():
    """Cài đặt WNTR (Water Network Tool for Resilience)"""
    print("📦 Cài đặt WNTR...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "wntr"])
        print("✅ WNTR đã được cài đặt thành công")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Lỗi cài đặt WNTR: {e}")
        return False

def install_epanet_python():
    """Cài đặt epanet-python"""
    print("📦 Cài đặt epanet-python...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "epanet-python"])
        print("✅ epanet-python đã được cài đặt thành công")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Lỗi cài đặt epanet-python: {e}")
        return False

def download_epanet_toolkit():
    """Tải EPANET Toolkit từ EPA"""
    print("📥 Tải EPANET Toolkit...")
    
    system = platform.system().lower()
    
    if system == "windows":
        # Tải EPANET Toolkit cho Windows
        url = "https://www.epa.gov/sites/default/files/2016-12/epanet2_installer.exe"
        filename = "epanet2_installer.exe"
    elif system == "linux":
        # Tải EPANET Toolkit cho Linux
        url = "https://github.com/OpenWaterAnalytics/EPANET/releases/download/v2.2/epanet2.2.0-linux.tar.gz"
        filename = "epanet2.2.0-linux.tar.gz"
    elif system == "darwin":  # macOS
        # Tải EPANET Toolkit cho macOS
        url = "https://github.com/OpenWaterAnalytics/EPANET/releases/download/v2.2/epanet2.2.0-macos.tar.gz"
        filename = "epanet2.2.0-macos.tar.gz"
    else:
        print(f"❌ Hệ điều hành {system} không được hỗ trợ")
        return False
    
    try:
        print(f"Tải từ: {url}")
        urllib.request.urlretrieve(url, filename)
        print(f"✅ Đã tải {filename}")
        
        if filename.endswith('.tar.gz'):
            # Giải nén file tar.gz
            import tarfile
            with tarfile.open(filename, 'r:gz') as tar:
                tar.extractall()
            print("✅ Đã giải nén EPANET Toolkit")
        elif filename.endswith('.exe'):
            print("✅ Đã tải EPANET installer. Vui lòng chạy file .exe để cài đặt")
        
        return True
        
    except Exception as e:
        print(f"❌ Lỗi tải EPANET Toolkit: {e}")
        return False

def check_epanet_installation():
    """Kiểm tra EPANET đã được cài đặt chưa"""
    print("🔍 Kiểm tra EPANET...")
    
    # Kiểm tra WNTR
    try:
        import wntr
        print("✅ WNTR đã được cài đặt")
        return True
    except ImportError:
        pass
    
    # Kiểm tra epanet-python
    try:
        import epanet
        print("✅ epanet-python đã được cài đặt")
        return True
    except ImportError:
        pass
    
    # Kiểm tra EPANET Toolkit
    if os.path.exists("epanet2.dll") or os.path.exists("libepanet.so"):
        print("✅ EPANET Toolkit đã được cài đặt")
        return True
    
    print("❌ EPANET chưa được cài đặt")
    return False

def main():
    """Hàm chính"""
    print("🚀 Cài đặt EPANET cho Python")
    print("=" * 50)
    
    # Kiểm tra EPANET đã cài đặt chưa
    if check_epanet_installation():
        print("✅ EPANET đã được cài đặt")
        return
    
    print("📋 Các tùy chọn cài đặt:")
    print("1. WNTR (Water Network Tool for Resilience) - Khuyến nghị")
    print("2. epanet-python")
    print("3. Tải EPANET Toolkit từ EPA")
    print("4. Tất cả")
    
    choice = input("\nChọn tùy chọn (1-4): ").strip()
    
    if choice == "1":
        install_wntr()
    elif choice == "2":
        install_epanet_python()
    elif choice == "3":
        download_epanet_toolkit()
    elif choice == "4":
        install_wntr()
        install_epanet_python()
        download_epanet_toolkit()
    else:
        print("❌ Lựa chọn không hợp lệ")
        return
    
    print("\n" + "=" * 50)
    print("🎉 Hoàn thành cài đặt!")
    print("\n📝 Lưu ý:")
    print("- Nếu cài đặt WNTR, sử dụng: import wntr")
    print("- Nếu cài đặt epanet-python, sử dụng: import epanet")
    print("- Nếu tải EPANET Toolkit, cần cài đặt thủ công")

if __name__ == "__main__":
    main()
