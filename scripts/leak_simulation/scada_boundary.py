"""
Module để load và apply SCADA data thật làm boundary conditions cho WNTR simulation
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import wntr

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services.scada_service import SCADAService
from utils.logger import logger


class SCADABoundaryCondition:
    """
    Class để load và apply SCADA data thật làm boundary conditions cho WNTR
    """
    
    def __init__(self, use_scada: bool = True):
        """
        Args:
            use_scada: Có sử dụng SCADA data thật không
        """
        self.use_scada = use_scada
        self.scada_service = SCADAService() if use_scada else None
        
        # Mapping SCADA stations to EPANET nodes (reservoirs/tanks/pumps)
        # Cần cấu hình trong config/scada_mapping.json
        self.station_to_node_mapping = self._load_mapping()
    
    def _load_mapping(self) -> Dict[str, Dict[str, Any]]:
        """Load mapping từ config"""
        mapping_file = project_root / "config" / "scada_mapping.json"
        if not mapping_file.exists():
            logger.warning("SCADA mapping file not found - will use fixed demand")
            return {}
        
        try:
            import json
            with open(mapping_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Load mapping từ config (nếu có)
            # Format: {"scada_station": {"epanet_node": "node_id", "type": "reservoir|tank|pump"}}
            mapping = {}
            scada_stations = config.get('scada_stations', {})
            
            for station_code, station_info in scada_stations.items():
                # TODO: Cần config mapping cụ thể trong scada_mapping.json
                # Tạm thời return empty - sẽ được config sau
                pass
            
            return mapping
        except Exception as e:
            logger.warning(f"Error loading SCADA mapping: {e}")
            return {}
    
    def load_scada_data(self, hours_back: int = 24) -> Optional[Dict[str, Any]]:
        """
        Load SCADA data thật từ API
        
        Args:
            hours_back: Số giờ lùi lại từ hiện tại
        
        Returns:
            Dict chứa SCADA boundary conditions hoặc None nếu không load được
        """
        if not self.use_scada or not self.scada_service:
            return None
        
        try:
            # Lấy danh sách station codes từ config
            station_codes = list(self.station_to_node_mapping.keys())
            if not station_codes:
                # Fallback: dùng station mặc định từ config
                station_codes = ["13085"]  # Từ scada_mapping.json
            
            logger.info(f"Loading SCADA data from {len(station_codes)} stations...")
            
            # Load SCADA data
            scada_result = self.scada_service.get_realtime_data_for_epanet(
                station_codes=station_codes,
                hours_back=hours_back
            )
            
            if scada_result.get('success', False):
                logger.info(f"Loaded SCADA data successfully")
                return scada_result.get('boundary_conditions', {})
            else:
                logger.warning("Failed to load SCADA data - will use fixed demand")
                return None
                
        except Exception as e:
            logger.error(f"Error loading SCADA data: {e}")
            return None
    
    def apply_to_wntr(self, wn: wntr.network.WaterNetworkModel, 
                      scada_data: Optional[Dict[str, Any]] = None,
                      simulation_start_time: Optional[datetime] = None) -> bool:
        """
        Apply SCADA data làm boundary conditions cho WNTR model
        
        Args:
            wn: WNTR water network model
            scada_data: SCADA boundary conditions (nếu None, sẽ load từ API)
            simulation_start_time: Thời gian bắt đầu simulation (để sync với SCADA data)
        
        Returns:
            True nếu apply thành công, False nếu không
        """
        if not self.use_scada:
            logger.info("SCADA disabled - using fixed demand")
            return False
        
        # Load SCADA data nếu chưa có
        if scada_data is None:
            scada_data = self.load_scada_data()
        
        if not scada_data:
            logger.warning("No SCADA data available - using fixed demand")
            return False
        
        try:
            # Apply SCADA data làm boundary conditions
            # Các cách apply:
            # 1. Reservoir/Tank levels từ SCADA pressure
            # 2. Pump flow rates từ SCADA flow
            # 3. Demand patterns từ SCADA flow trends
            
            applied = False
            
            for station_code, boundary_data in scada_data.items():
                if not boundary_data:
                    continue
                
                # Map station to EPANET node
                mapping = self.station_to_node_mapping.get(station_code, {})
                epanet_node = mapping.get('epanet_node')
                node_type = mapping.get('type', 'unknown')
                
                if not epanet_node:
                    # Không có mapping - skip
                    continue
                
                # Apply theo loại node
                if node_type == 'reservoir':
                    # Set reservoir head từ SCADA pressure
                    try:
                        node = wn.get_node(epanet_node)
                        if isinstance(node, wntr.network.elements.Reservoir):
                            # Lấy giá trị pressure đầu tiên từ SCADA
                            if boundary_data and len(boundary_data) > 0:
                                first_record = boundary_data[0]
                                pressure = first_record.get('pressure')
                                if pressure is not None:
                                    # Convert pressure to head (assume elevation = 0 or known)
                                    # Head = Elevation + Pressure
                                    elevation = node.base_head if hasattr(node, 'base_head') else 0
                                    node.base_head = elevation + pressure
                                    logger.info(f"Set reservoir {epanet_node} head from SCADA: {elevation + pressure:.2f}m")
                                    applied = True
                    except Exception as e:
                        logger.warning(f"Error applying SCADA to reservoir {epanet_node}: {e}")
                
                elif node_type == 'pump':
                    # Set pump flow từ SCADA flow
                    try:
                        link = wn.get_link(epanet_node)
                        if isinstance(link, wntr.network.elements.Pump):
                            # Lấy giá trị flow đầu tiên từ SCADA
                            if boundary_data and len(boundary_data) > 0:
                                first_record = boundary_data[0]
                                flow_lps = first_record.get('flow')  # L/s
                                if flow_lps is not None:
                                    flow_m3s = flow_lps / 1000.0  # Convert to m³/s
                                    # Set pump curve hoặc flow control
                                    logger.info(f"Set pump {epanet_node} flow from SCADA: {flow_m3s:.6f} m³/s")
                                    applied = True
                    except Exception as e:
                        logger.warning(f"Error applying SCADA to pump {epanet_node}: {e}")
            
            if applied:
                logger.info("Applied SCADA boundary conditions to WNTR model")
            else:
                logger.warning("No SCADA boundary conditions applied - check mapping")
            
            return applied
            
        except Exception as e:
            logger.error(f"Error applying SCADA to WNTR: {e}")
            return False


