import logging
import sys
from datetime import datetime
from typing import Optional

class EPANETLogger:
    def __init__(self, name: str = "epanet_api"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Tạo formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        # File handler
        file_handler = logging.FileHandler('logs/epanet_api.log', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        
        # Thêm handlers
        if not self.logger.handlers:
            self.logger.addHandler(console_handler)
            self.logger.addHandler(file_handler)
    
    def info(self, message: str, extra: Optional[dict] = None):
        """Log thông tin"""
        self.logger.info(message, extra=extra)
    
    def warning(self, message: str, extra: Optional[dict] = None):
        """Log cảnh báo"""
        self.logger.warning(message, extra=extra)
    
    def error(self, message: str, extra: Optional[dict] = None):
        """Log lỗi"""
        self.logger.error(message, extra=extra)
    
    def debug(self, message: str, extra: Optional[dict] = None):
        """Log debug"""
        self.logger.debug(message, extra=extra)
    
    def simulation_start(self, run_id: int, duration: int):
        """Log bắt đầu mô phỏng"""
        self.info(f"Starting simulation {run_id} - Duration: {duration}h")
    
    def simulation_complete(self, run_id: int, duration: float):
        """Log hoàn thành mô phỏng"""
        self.info(f"Simulation {run_id} completed - Duration: {duration:.2f}s")
    
    def simulation_failed(self, run_id: int, error: str):
        """Log thất bại mô phỏng"""
        self.error(f"Simulation {run_id} failed: {error}")
    
    def data_received(self, node_count: int, data_type: str):
        """Log nhận dữ liệu"""
        self.info(f"Received {data_type} for {node_count} nodes")
    
    def api_request(self, method: str, endpoint: str, status_code: int):
        """Log API request"""
        self.info(f"API {method} {endpoint} - Status: {status_code}")

# Global logger instance
logger = EPANETLogger()

# Tạo thư mục logs nếu chưa có
import os
os.makedirs('logs', exist_ok=True)
