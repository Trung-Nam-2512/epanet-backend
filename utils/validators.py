from typing import List, Dict, Any, Optional
import re
from models.schemas import NodeData

class EPANETValidator:
    """Validator cho dữ liệu EPANET"""
    
    @staticmethod
    def validate_node_id(node_id: str) -> bool:
        """Kiểm tra ID nút hợp lệ"""
        if not node_id or not isinstance(node_id, str):
            return False
        
        # ID nút phải là số hoặc chữ cái
        return bool(re.match(r'^[A-Za-z0-9_]+$', node_id))
    
    @staticmethod
    def validate_pressure(pressure: float) -> bool:
        """Kiểm tra áp lực hợp lệ (0-100m)"""
        return isinstance(pressure, (int, float)) and 0 <= pressure <= 100
    
    @staticmethod
    def validate_flow(flow: float) -> bool:
        """Kiểm tra lưu lượng hợp lệ (-1000 đến 1000 LPS)"""
        return isinstance(flow, (int, float)) and -1000 <= flow <= 1000
    
    @staticmethod
    def validate_demand(demand: float) -> bool:
        """Kiểm tra nhu cầu hợp lệ (0-1000 LPS)"""
        return isinstance(demand, (int, float)) and 0 <= demand <= 1000
    
    @staticmethod
    def validate_head(head: float) -> bool:
        """Kiểm tra cột áp hợp lệ (0-200m)"""
        return isinstance(head, (int, float)) and 0 <= head <= 200
    
    @staticmethod
    def validate_simulation_duration(duration: int) -> bool:
        """Kiểm tra thời gian mô phỏng hợp lệ (1-168 giờ)"""
        return isinstance(duration, int) and 1 <= duration <= 168
    
    @staticmethod
    def validate_timestep(timestep: int) -> bool:
        """Kiểm tra bước thời gian hợp lệ (1-24 giờ)"""
        return isinstance(timestep, int) and 1 <= timestep <= 24
    
    @staticmethod
    def validate_demand_multiplier(multiplier: float) -> bool:
        """Kiểm tra hệ số nhân nhu cầu hợp lệ (0.1-10.0)"""
        return isinstance(multiplier, (int, float)) and 0.1 <= multiplier <= 10.0
    
    @staticmethod
    def validate_node_data(node_data: NodeData) -> Dict[str, List[str]]:
        """Kiểm tra dữ liệu nút và trả về lỗi"""
        errors = []
        
        if not EPANETValidator.validate_node_id(node_data.node_id):
            errors.append("ID nút không hợp lệ")
        
        if node_data.pressure is not None and not EPANETValidator.validate_pressure(node_data.pressure):
            errors.append("Áp lực không hợp lệ (0-100m)")
        
        if node_data.flow is not None and not EPANETValidator.validate_flow(node_data.flow):
            errors.append("Lưu lượng không hợp lệ (-1000 đến 1000 LPS)")
        
        if node_data.demand is not None and not EPANETValidator.validate_demand(node_data.demand):
            errors.append("Nhu cầu không hợp lệ (0-1000 LPS)")
        
        if node_data.head is not None and not EPANETValidator.validate_head(node_data.head):
            errors.append("Cột áp không hợp lệ (0-200m)")
        
        return {"errors": errors}
    
    @staticmethod
    def validate_network_data(nodes_data: List[NodeData]) -> Dict[str, Any]:
        """Kiểm tra dữ liệu mạng lưới"""
        total_errors = []
        valid_nodes = 0
        invalid_nodes = 0
        
        for node_data in nodes_data:
            node_errors = EPANETValidator.validate_node_data(node_data)
            if node_errors["errors"]:
                invalid_nodes += 1
                total_errors.extend([f"{node_data.node_id}: {error}" for error in node_errors["errors"]])
            else:
                valid_nodes += 1
        
        return {
            "valid_nodes": valid_nodes,
            "invalid_nodes": invalid_nodes,
            "total_errors": len(total_errors),
            "errors": total_errors
        }
    
    @staticmethod
    def sanitize_node_id(node_id: str) -> str:
        """Làm sạch ID nút"""
        if not node_id:
            return ""
        
        # Loại bỏ ký tự đặc biệt, chỉ giữ lại chữ cái, số và dấu gạch dưới
        sanitized = re.sub(r'[^A-Za-z0-9_]', '', str(node_id))
        return sanitized.strip()
    
    @staticmethod
    def normalize_pressure(pressure: float) -> float:
        """Chuẩn hóa áp lực"""
        if pressure < 0:
            return 0.0
        elif pressure > 100:
            return 100.0
        return round(float(pressure), 2)
    
    @staticmethod
    def normalize_flow(flow: float) -> float:
        """Chuẩn hóa lưu lượng"""
        if flow < -1000:
            return -1000.0
        elif flow > 1000:
            return 1000.0
        return round(float(flow), 3)
    
    @staticmethod
    def normalize_demand(demand: float) -> float:
        """Chuẩn hóa nhu cầu"""
        if demand < 0:
            return 0.0
        elif demand > 1000:
            return 1000.0
        return round(float(demand), 3)
