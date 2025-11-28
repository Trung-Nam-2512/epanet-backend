"""
Module nạp và validate mô hình EPANET từ file .inp
"""
import os
import io
from typing import Dict, List, Optional, Tuple
import wntr
import wntr.network.elements
from utils.logger import logger


class ModelLoader:
    """Class để nạp và validate mô hình EPANET"""
    
    def __init__(self, inp_path: str):
        self.inp_path = inp_path
        self.wn = None
        self.model_bytes = None
        
    def load_and_validate(self) -> Tuple[bool, str]:
        """
        Nạp mô hình và kiểm tra headers
        
        Returns:
            (success, message)
        """
        try:
            # Kiểm tra file tồn tại
            if not os.path.exists(self.inp_path):
                return False, f"File không tồn tại: {self.inp_path}"
            
            # Đọc file để kiểm tra headers
            with open(self.inp_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Validate headers - kiểm tra các section bắt buộc
            required_sections = [
                '[TITLE]',
                '[JUNCTIONS]',
                '[PIPES]',
                '[PATTERNS]'
            ]
            
            missing_sections = []
            for section in required_sections:
                if section not in content:
                    missing_sections.append(section)
            
            if missing_sections:
                error_msg = f"File .inp thiếu các section bắt buộc: {', '.join(missing_sections)}"
                logger.error(error_msg)
                return False, error_msg
            
            # Đếm số lượng headers/sections để phát hiện dữ liệu bẩn
            sections_count = content.count('[')
            if sections_count < 5:
                warning = f"Cảnh báo: File .inp có ít section ({sections_count}). Có thể dữ liệu không đầy đủ."
                logger.warning(warning)
                return False, warning
            
            # Nạp mô hình bằng WNTR
            try:
                self.wn = wntr.network.WaterNetworkModel(self.inp_path)
                logger.info(f"Nạp mô hình thành công: {len(self.wn.node_name_list)} nodes, {len(self.wn.pipe_name_list)} pipes")
            except Exception as e:
                error_msg = f"Lỗi khi nạp mô hình bằng WNTR: {str(e)}"
                logger.error(error_msg)
                return False, error_msg
            
            # Lưu model dạng bytes để tái sử dụng (tránh đọc file nhiều lần)
            self._save_model_bytes()
            
            return True, "Mô hình đã được nạp và validate thành công"
            
        except Exception as e:
            error_msg = f"Lỗi khi nạp mô hình: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def _save_model_bytes(self):
        """Lưu mô hình dạng bytes để có thể tạo bản sao"""
        try:
            # Ghi model ra file tạm rồi đọc lại bytes
            import tempfile
            tmp_file = None
            try:
                # Tạo file tạm với delete=False để có thể mở lại
                tmp_fd, tmp_path = tempfile.mkstemp(suffix='.inp', text=False)
                tmp_file = tmp_path
                
                # Ghi model ra file
                wntr.network.io.write_inpfile(self.wn, tmp_path)
                
                # Đọc lại bytes
                with open(tmp_path, 'rb') as f:
                    self.model_bytes = f.read()
                
                # Đóng file descriptor và xóa file
                try:
                    os.close(tmp_fd)
                except:
                    pass
                
                # Xóa file - thử nhiều lần nếu cần (Windows issue)
                max_retries = 3
                for i in range(max_retries):
                    try:
                        os.unlink(tmp_path)
                        break
                    except PermissionError:
                        if i < max_retries - 1:
                            import time
                            time.sleep(0.1)
                        else:
                            logger.warning(f"Không thể xóa file tạm {tmp_path}")
            
            except Exception as e:
                if tmp_file and os.path.exists(tmp_file):
                    try:
                        os.unlink(tmp_file)
                    except:
                        pass
                raise e
            
            logger.info(f"Đã lưu model dạng bytes ({len(self.model_bytes)} bytes)")
        except Exception as e:
            logger.warning(f"Không thể lưu model bytes: {str(e)}. Sẽ dùng file gốc.")
            self.model_bytes = None
    
    def create_model_copy(self) -> Optional[wntr.network.WaterNetworkModel]:
        """
        Tạo bản sao mô hình từ bytes (hoặc file gốc nếu không có bytes)
        
        Returns:
            WaterNetworkModel mới
        """
        try:
            if self.model_bytes:
                # Tạo model từ bytes
                import tempfile
                with tempfile.NamedTemporaryFile(mode='wb', suffix='.inp', delete=False) as tmp_file:
                    tmp_file.write(self.model_bytes)
                    tmp_path = tmp_file.name
                
                wn_copy = wntr.network.WaterNetworkModel(tmp_path)
                os.unlink(tmp_path)
                return wn_copy
            else:
                # Fallback: dùng file gốc
                return wntr.network.WaterNetworkModel(self.inp_path)
        except Exception as e:
            logger.error(f"Lỗi khi tạo model copy: {str(e)}")
            return None
    
    def get_junction_nodes(self) -> List[str]:
        """Lấy danh sách tất cả junction nodes"""
        if not self.wn:
            return []
        
        junctions = []
        for node_name in self.wn.node_name_list:
            node = self.wn.get_node(node_name)
            # Kiểm tra bằng isinstance hoặc so sánh với int
            if isinstance(node, wntr.network.elements.Junction):
                junctions.append(node_name)
        
        return junctions
    
    def get_all_nodes(self) -> List[str]:
        """Lấy danh sách tất cả nodes"""
        if not self.wn:
            return []
        return list(self.wn.node_name_list)

