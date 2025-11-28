"""
Module thêm nhiễu Gaussian vào dữ liệu đo (áp lực, lưu lượng)
"""
import numpy as np
from typing import Dict, List, Any
from utils.logger import logger


class NoiseInjector:
    """Class để thêm nhiễu vào dữ liệu đo"""
    
    def __init__(self, pressure_sigma: float, flow_sigma: float, enabled: bool = True):
        """
        Args:
            pressure_sigma: Độ lệch chuẩn nhiễu cho áp lực (m)
            flow_sigma: Độ lệch chuẩn nhiễu cho lưu lượng (LPS)
            enabled: Bật/tắt nhiễu
        """
        self.pressure_sigma = pressure_sigma
        self.flow_sigma = flow_sigma
        self.enabled = enabled
    
    def inject_noise(self, simulation_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Thêm nhiễu vào kết quả mô phỏng
        
        Args:
            simulation_results: Kết quả mô phỏng từ WNTR
        
        Returns:
            Kết quả đã thêm nhiễu
        """
        if not self.enabled:
            return simulation_results
        
        noisy_results = {
            'nodes': {},
            'pipes': {},
            'timestamps': simulation_results.get('timestamps', [])
        }
        
        # Thêm nhiễu cho nodes (áp lực, lưu lượng)
        for node_name, node_data in simulation_results.get('nodes', {}).items():
            noisy_node_data = []
            for record in node_data:
                noisy_record = record.copy()
                
                # Nhiễu áp lực
                if 'pressure' in noisy_record and noisy_record['pressure'] is not None:
                    pressure_noise = np.random.normal(0, self.pressure_sigma)
                    noisy_record['pressure'] = max(0, noisy_record['pressure'] + pressure_noise)
                    noisy_record['pressure_raw'] = record['pressure']  # Giữ giá trị gốc
                
                # Nhiễu demand/flow (nếu có)
                if 'demand' in noisy_record and noisy_record['demand'] is not None:
                    flow_noise = np.random.normal(0, self.flow_sigma)
                    noisy_record['demand'] = max(0, noisy_record['demand'] + flow_noise)
                    noisy_record['demand_raw'] = record['demand']  # Giữ giá trị gốc
                
                noisy_node_data.append(noisy_record)
            
            noisy_results['nodes'][node_name] = noisy_node_data
        
        # Thêm nhiễu cho pipes (lưu lượng)
        for pipe_name, pipe_data in simulation_results.get('pipes', {}).items():
            noisy_pipe_data = []
            for record in pipe_data:
                noisy_record = record.copy()
                
                # Nhiễu lưu lượng
                if 'flow' in noisy_record and noisy_record['flow'] is not None:
                    flow_noise = np.random.normal(0, self.flow_sigma)
                    noisy_record['flow'] = noisy_record['flow'] + flow_noise  # Có thể âm
                    noisy_record['flow_raw'] = record['flow']  # Giữ giá trị gốc
                
                noisy_pipe_data.append(noisy_record)
            
            noisy_results['pipes'][pipe_name] = noisy_pipe_data
        
        logger.info("Đã thêm nhiễu Gaussian vào dữ liệu đo")
        return noisy_results

