"""
Service để apply SCADA data làm boundary conditions cho WNTR simulation
"""
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import wntr
import pandas as pd
import numpy as np

from utils.logger import logger


class SCADABoundaryService:
    """
    Service để load và apply SCADA data thật làm boundary conditions cho WNTR
    """
    
    def __init__(self):
        """Initialize SCADA boundary service"""
        self.mapping_config = self._load_mapping_config()
        logger.info(f"Loaded SCADA boundary mapping for {len(self.mapping_config)} stations")
    
    def _load_mapping_config(self) -> Dict[str, Dict[str, Any]]:
        """Load mapping configuration từ scada_mapping.json"""
        mapping_file = Path("config/scada_mapping.json")
        if not mapping_file.exists():
            logger.warning("SCADA mapping file not found - SCADA boundary conditions will not be applied")
            return {}
        
        try:
            with open(mapping_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            mapping = {}
            scada_stations = config.get('scada_stations', {})
            
            for station_code, station_info in scada_stations.items():
                epanet_mapping = station_info.get('epanet_mapping', {})
                if epanet_mapping:
                    mapping[station_code] = {
                        'epanet_node': epanet_mapping.get('epanet_node'),
                        'node_type': epanet_mapping.get('node_type', 'unknown'),
                        'apply_pressure_as_head': epanet_mapping.get('apply_pressure_as_head', False),
                        'apply_flow': epanet_mapping.get('apply_flow', False),
                        'pressure_type': epanet_mapping.get('pressure_type', 'absolute'),  # Fix: Load pressure_type
                        'elevation': epanet_mapping.get('elevation', 0.0),  # Fix: Load elevation
                        'description': epanet_mapping.get('description', '')
                    }
                    logger.info(f"Mapped SCADA station {station_code} -> EPANET {epanet_mapping.get('node_type')} {epanet_mapping.get('epanet_node')}")
                else:
                    logger.warning(f"SCADA station {station_code} has no epanet_mapping configuration")
            
            return mapping
            
        except Exception as e:
            logger.error(f"Error loading SCADA mapping config: {e}")
            return {}
    
    def apply_scada_boundary_conditions(
        self, 
        wn: wntr.network.WaterNetworkModel,
        scada_boundary_data: Dict[str, List[Dict[str, Any]]],
        simulation_duration_hours: int,
        hydraulic_timestep_hours: int = 1,
        simulation_start_time: Optional[datetime] = None
    ) -> bool:
        """
        Apply SCADA boundary conditions vào WNTR model
        
        Args:
            wn: WNTR water network model
            scada_boundary_data: Dict với key là station_code, value là list các records với pressure/flow theo time
            simulation_duration_hours: Thời gian simulation (giờ)
            hydraulic_timestep_hours: Bước thời gian thủy lực (giờ)
        
        Returns:
            True nếu apply thành công ít nhất một boundary condition, False nếu không
        """
        if not scada_boundary_data:
            logger.info("No SCADA boundary data provided - using INP file boundary conditions")
            return False
        
        if not self.mapping_config:
            logger.warning("No SCADA mapping configuration - cannot apply boundary conditions")
            return False
        
        applied_count = 0
        
        try:
            for station_code, boundary_records in scada_boundary_data.items():
                if not boundary_records:
                    continue
                
                # Get mapping for this station
                mapping = self.mapping_config.get(station_code)
                if not mapping:
                    logger.warning(f"No mapping found for SCADA station {station_code} - skipping")
                    continue
                
                epanet_node = mapping.get('epanet_node')
                node_type = mapping.get('node_type')
                
                if not epanet_node:
                    logger.warning(f"Mapping for station {station_code} has no epanet_node - skipping")
                    continue
                
                # Apply based on node type
                if node_type == 'reservoir':
                    if self._apply_reservoir_boundary(wn, epanet_node, boundary_records, 
                                                      simulation_duration_hours, hydraulic_timestep_hours, mapping,
                                                      simulation_start_time=simulation_start_time):
                        applied_count += 1
                        logger.info(f"[OK] Applied SCADA boundary condition: station {station_code} -> reservoir {epanet_node}")
                
                elif node_type == 'tank':
                    if self._apply_tank_boundary(wn, epanet_node, boundary_records,
                                                simulation_duration_hours, hydraulic_timestep_hours, mapping):
                        applied_count += 1
                        logger.info(f"✅ Applied SCADA boundary condition: station {station_code} → tank {epanet_node}")
                
                elif node_type == 'pump':
                    if self._apply_pump_boundary(wn, epanet_node, boundary_records, mapping):
                        applied_count += 1
                        logger.info(f"✅ Applied SCADA boundary condition: station {station_code} → pump {epanet_node}")
                
                else:
                    logger.warning(f"Unknown node type '{node_type}' for station {station_code} - skipping")
            
            if applied_count > 0:
                logger.info(f"[OK] Successfully applied {applied_count} SCADA boundary condition(s)")
                return True
            else:
                logger.warning("No SCADA boundary conditions were applied - check mapping configuration")
                return False
                
        except Exception as e:
            logger.error(f"Error applying SCADA boundary conditions: {e}")
            return False
    
    def _apply_reservoir_boundary(
        self,
        wn: wntr.network.WaterNetworkModel,
        epanet_node: str,
        boundary_records: List[Dict[str, Any]],
        simulation_duration_hours: int,
        hydraulic_timestep_hours: int,
        mapping: Dict[str, Any],
        simulation_start_time: Optional[datetime] = None
    ) -> bool:
        """
        Apply SCADA data làm boundary condition cho reservoir
        
        Args:
            wn: WNTR network model
            epanet_node: EPANET node ID (reservoir)
            boundary_records: List các SCADA records theo thời gian
            simulation_duration_hours: Thời gian simulation
            hydraulic_timestep_hours: Bước thời gian
            mapping: Mapping configuration
        
        Returns:
            True nếu apply thành công
        """
        try:
            node = wn.get_node(epanet_node)
            if not isinstance(node, wntr.network.elements.Reservoir):
                logger.error(f"Node {epanet_node} is not a Reservoir - cannot apply SCADA boundary")
                return False
            
            # Lưu base_head ban đầu từ file .inp (đây là elevation cố định)
            initial_base_head = node.base_head
            logger.info(f"[SCADA] ====== RESERVOIR {epanet_node} BOUNDARY APPLICATION ======")
            logger.info(f"[SCADA] Initial base_head from .inp file: {initial_base_head:.2f}m")
            logger.info(f"[SCADA] Boundary records count: {len(boundary_records)}")
            
            apply_pressure = mapping.get('apply_pressure_as_head', False)
            
            if not apply_pressure:
                logger.info(f"Reservoir {epanet_node}: apply_pressure_as_head is False - skipping")
                return False
            
            # Build time-series từ SCADA data
            # Tạo time index cho simulation
            time_steps = []
            head_values = []
            
            # Parse timestamps từ SCADA records
            scada_times = []
            scada_pressures = []
            
            for record in boundary_records:
                timestamp_str = record.get('timestamp')
                pressure = record.get('pressure')
                
                if timestamp_str and pressure is not None:
                    try:
                        # Parse timestamp (format: "2025-01-15 10:00" hoặc ISO format)
                        if 'T' in timestamp_str:
                            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        else:
                            dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M")
                        
                        scada_times.append(dt)
                        scada_pressures.append(float(pressure))
                    except Exception as e:
                        logger.warning(f"Error parsing timestamp {timestamp_str}: {e}")
                        continue
            
            if not scada_times:
                logger.warning(f"No valid SCADA data with timestamps for reservoir {epanet_node}")
                # Fallback: dùng giá trị đầu tiên với proper conversion
                if boundary_records:
                    first_record = boundary_records[0]
                    pressure = first_record.get('pressure')
                    if pressure is not None:
                        # Fix: Apply pressure conversion (absolute/gauge)
                        pressure_value = float(pressure)
                        pressure_type = mapping.get('pressure_type', 'absolute')
                        if pressure_type == 'gauge':
                            # Elevation là giá trị CỐ ĐỊNH từ file .inp
                            elevation = initial_base_head  # Lấy từ file .inp
                            new_head = elevation + pressure_value
                            logger.info(f"[SCADA] Fallback - Gauge pressure conversion for {epanet_node}:")
                            logger.info(f"  Elevation (from .inp): {elevation:.2f}m")
                            logger.info(f"  SCADA P1 (gauge): {pressure_value:.2f}m")
                            logger.info(f"  Absolute Head: {new_head:.2f}m")
                        else:
                            new_head = pressure_value
                            logger.info(f"[SCADA] Fallback - Using absolute head {new_head:.2f}m for {epanet_node}")
                        node.base_head = new_head
                        logger.info(f"[SCADA] Applied constant head {new_head:.2f}m to reservoir {epanet_node} from SCADA (fallback - no timestamps)")
                        return True
                return False
            
            # Tạo time-series cho simulation
            # Fix: Sync simulation time với SCADA data time
            if simulation_start_time is None:
                # Nếu không có simulation_start_time, dùng timestamp từ SCADA data đầu tiên
                if scada_times:
                    simulation_start = scada_times[0].replace(minute=0, second=0, microsecond=0)
                else:
                    # Fallback: dùng thời gian hiện tại
                    simulation_start = datetime.now().replace(minute=0, second=0, microsecond=0)
            else:
                simulation_start = simulation_start_time.replace(minute=0, second=0, microsecond=0)
            
            simulation_times = []
            simulation_heads = []
            
            # Tạo time steps cho simulation (mỗi hydraulic_timestep)
            for hour in range(0, simulation_duration_hours + 1, hydraulic_timestep_hours):
                sim_time = simulation_start + timedelta(hours=hour)
                simulation_times.append(hour * 3600)  # Convert to seconds
                
                # Tìm SCADA data gần nhất với thời gian này
                closest_pressure = None
                min_time_diff = float('inf')
                
                for scada_time, scada_pressure in zip(scada_times, scada_pressures):
                    time_diff = abs((scada_time - sim_time).total_seconds())
                    if time_diff < min_time_diff:
                        min_time_diff = time_diff
                        closest_pressure = scada_pressure
                
                if closest_pressure is not None:
                    # Fix: Validate pressure value và time difference
                    pressure_value = float(closest_pressure)
                    
                    # Validate time difference (max 24 hours)
                    max_time_diff_hours = 24
                    if min_time_diff > max_time_diff_hours * 3600:
                        logger.warning(f"SCADA data too old for {epanet_node} at {sim_time} (diff: {min_time_diff/3600:.1f}h) - using current head")
                        current_head = node.base_head if hasattr(node, 'base_head') else 0.0
                        simulation_heads.append(current_head)
                    # Validate pressure value range
                    elif pressure_value < 0:
                        logger.warning(f"Invalid pressure value {pressure_value}m for {epanet_node} at {sim_time} - using current head")
                        current_head = node.base_head if hasattr(node, 'base_head') else 0.0
                        simulation_heads.append(current_head)
                    elif pressure_value > 1000:  # Reasonable max head (1000m)
                        logger.warning(f"Suspiciously high pressure value {pressure_value}m for {epanet_node} at {sim_time} - using current head")
                        current_head = node.base_head if hasattr(node, 'base_head') else 0.0
                        simulation_heads.append(current_head)
                    else:
                        # Fix: Apply pressure as head với proper conversion
                        # Load pressure_type và elevation từ mapping (đã load từ config)
                        pressure_type = mapping.get('pressure_type', 'absolute')  # Default: absolute
                        if pressure_type == 'gauge':
                            # Gauge pressure: Head = Elevation + Pressure
                            # Elevation là giá trị CỐ ĐỊNH từ file .inp (base_head ban đầu)
                            # SCADA P1 là giá trị ĐỘNG (thay đổi theo thời gian)
                            elevation = initial_base_head  # Lấy từ file .inp (cố định)
                            head_value = elevation + pressure_value  # Head = Elevation (cố định) + Pressure (động)
                            logger.info(f"[SCADA] Gauge pressure conversion for {epanet_node}:")
                            logger.info(f"  Elevation (from .inp): {elevation:.2f}m (CỐ ĐỊNH)")
                            logger.info(f"  SCADA P1 (gauge): {pressure_value:.2f}m (ĐỘNG)")
                            logger.info(f"  Absolute Head: {head_value:.2f}m = {elevation:.2f}m + {pressure_value:.2f}m")
                        else:
                            # Absolute head: dùng trực tiếp (SCADA pressure đã là absolute head)
                            head_value = pressure_value
                            logger.info(f"[SCADA] Using absolute head {head_value:.2f}m directly from SCADA pressure for {epanet_node}")
                        
                        simulation_heads.append(head_value)
                else:
                    # Nếu không có data, dùng giá trị hiện tại
                    current_head = node.base_head if hasattr(node, 'base_head') else 0.0
                    simulation_heads.append(current_head)
            
            # Fix: Apply time-series head sử dụng WNTR Pattern
            if len(simulation_heads) > 1:
                try:
                    # WNTR Pattern sử dụng multipliers, không phải absolute values
                    # Strategy: base_head = giá trị đầu tiên, multipliers = ratios
                    base_head = simulation_heads[0]
                    
                    # Fix: WNTR Pattern multipliers phải là ratios so với base_head
                    # Nếu base_head = 0, dùng absolute values thay vì ratios
                    multipliers = []
                    if abs(base_head) > 0.001:  # base_head != 0
                        # Normal case: multipliers = ratios
                        for head_val in simulation_heads:
                            multiplier = head_val / base_head
                            multipliers.append(multiplier)
                    else:
                        # Special case: base_head = 0, dùng absolute values
                        # Set base_head = average và multipliers = ratios
                        avg_head = np.mean(simulation_heads)
                        if abs(avg_head) > 0.001:
                            base_head = avg_head
                            for head_val in simulation_heads:
                                multiplier = head_val / base_head
                                multipliers.append(multiplier)
                        else:
                            # All zeros - use constant 1.0 multipliers
                            multipliers = [1.0] * len(simulation_heads)
                    
                    # Tạo pattern name unique
                    pattern_name = f"SCADA_HEAD_{epanet_node}_{int(datetime.now().timestamp())}"
                    
                    # Get pattern timestep từ WNTR options
                    pattern_timestep_hours = wn.options.time.pattern_timestep / 3600 if hasattr(wn.options.time, 'pattern_timestep') else hydraulic_timestep_hours
                    
                    # Resample multipliers để match pattern timestep
                    # Nếu pattern_timestep != hydraulic_timestep, cần resample
                    if abs(pattern_timestep_hours - hydraulic_timestep_hours) > 0.01:
                        # Resample: tạo multipliers cho mỗi pattern timestep
                        num_pattern_steps = int(simulation_duration_hours / pattern_timestep_hours) + 1
                        resampled_multipliers = []
                        for i in range(num_pattern_steps):
                            pattern_time_hours = i * pattern_timestep_hours
                            # Tìm multiplier gần nhất
                            closest_idx = min(range(len(simulation_heads)), 
                                             key=lambda j: abs(j * hydraulic_timestep_hours - pattern_time_hours))
                            resampled_multipliers.append(multipliers[closest_idx])
                        multipliers = resampled_multipliers
                    
                    # Add pattern vào WNTR
                    wn.add_pattern(pattern_name, multipliers)
                    
                    # ✅ DEBUG: Log pattern details before setting
                    logger.info(f"[SCADA] Pattern {pattern_name} details:")
                    logger.info(f"  Pattern timestep: {pattern_timestep_hours:.2f} hours")
                    logger.info(f"  Hydraulic timestep: {hydraulic_timestep_hours:.2f} hours")
                    logger.info(f"  Number of multipliers: {len(multipliers)}")
                    logger.info(f"  Multipliers: {multipliers[:5]}... (first 5)")
                    
                    # Set reservoir head_timeseries
                    old_base_head = node.base_head
                    node.base_head = base_head
                    node.head_pattern_name = pattern_name
                    
                    # ✅ DEBUG: Verify head_timeseries after setting
                    logger.info(f"[SCADA] After setting head_timeseries:")
                    logger.info(f"  base_head: {node.base_head:.2f}m")
                    logger.info(f"  head_pattern_name: {node.head_pattern_name}")
                    logger.info(f"  Node elevation: {node.elevation:.2f}m" if hasattr(node, 'elevation') else "  Node has no elevation attribute")
                    if hasattr(node, 'head_timeseries'):
                        # Test head_timeseries.at() tại time 0
                        test_time = 0
                        test_head = node.head_timeseries.at(test_time)
                        logger.info(f"  head_timeseries.at(0): {test_head:.2f}m (expected: {base_head:.2f}m)")
                        # Check if head_timeseries includes elevation
                        if abs(test_head - base_head) > 0.01:
                            logger.warning(f"  ⚠️ WARNING: head_timeseries.at(0) = {test_head:.2f}m != base_head {base_head:.2f}m")
                            logger.warning(f"  Difference: {abs(test_head - base_head):.2f}m (could be elevation?)")
                    
                    logger.info(f"[SCADA] ✅ Applied time-varying head to reservoir {epanet_node} using pattern {pattern_name}")
                    logger.info(f"[SCADA]   Old base_head (from INP): {old_base_head:.2f}m")
                    logger.info(f"[SCADA]   New base_head (from SCADA): {base_head:.2f}m")
                    logger.info(f"[SCADA]   Pattern multipliers: {len(multipliers)} time steps, range: {min(multipliers):.3f} - {max(multipliers):.3f}")
                    logger.info(f"[SCADA]   Head range: {min(simulation_heads):.2f}m - {max(simulation_heads):.2f}m")
                    logger.info(f"[SCADA]   First head value: {simulation_heads[0]:.2f}m, Last head value: {simulation_heads[-1]:.2f}m")
                    logger.info(f"[SCADA] ====== END RESERVOIR {epanet_node} BOUNDARY APPLICATION ======")
                    
                except Exception as e:
                    logger.warning(f"Error creating head timeseries pattern for reservoir {epanet_node}: {e}")
                    import traceback
                    traceback.print_exc()
                    # Fallback: dùng giá trị đầu tiên
                    if simulation_heads:
                        node.base_head = simulation_heads[0]
                        logger.info(f"Applied first head value {simulation_heads[0]:.2f}m to reservoir {epanet_node} (fallback)")
            else:
                # Single value
                if simulation_heads:
                    old_base_head = node.base_head
                    node.base_head = simulation_heads[0]
                    logger.info(f"[SCADA] ✅ Applied constant head to reservoir {epanet_node}")
                    logger.info(f"[SCADA]   Old base_head (from INP): {old_base_head:.2f}m")
                    logger.info(f"[SCADA]   New base_head (from SCADA): {simulation_heads[0]:.2f}m")
                    logger.info(f"[SCADA] ====== END RESERVOIR {epanet_node} BOUNDARY APPLICATION ======")
            
            return True
            
        except Exception as e:
            logger.error(f"Error applying reservoir boundary for {epanet_node}: {e}")
            return False
    
    def _apply_tank_boundary(
        self,
        wn: wntr.network.WaterNetworkModel,
        epanet_node: str,
        boundary_records: List[Dict[str, Any]],
        simulation_duration_hours: int,
        hydraulic_timestep_hours: int,
        mapping: Dict[str, Any]
    ) -> bool:
        """
        Apply SCADA data làm boundary condition cho tank
        """
        try:
            node = wn.get_node(epanet_node)
            if not isinstance(node, wntr.network.elements.Tank):
                logger.error(f"Node {epanet_node} is not a Tank - cannot apply SCADA boundary")
                return False
            
            # Similar logic to reservoir but for tank level
            # For now, use first value as initial level
            if boundary_records:
                first_record = boundary_records[0]
                pressure = first_record.get('pressure')
                if pressure is not None:
                    # Convert pressure to level (simplified)
                    node.init_level = float(pressure)
                    logger.info(f"Applied initial level {float(pressure):.2f}m to tank {epanet_node} from SCADA")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error applying tank boundary for {epanet_node}: {e}")
            return False
    
    def _apply_pump_boundary(
        self,
        wn: wntr.network.WaterNetworkModel,
        epanet_node: str,
        boundary_records: List[Dict[str, Any]],
        mapping: Dict[str, Any]
    ) -> bool:
        """
        Apply SCADA data làm boundary condition cho pump
        """
        try:
            link = wn.get_link(epanet_node)
            if not isinstance(link, wntr.network.elements.Pump):
                logger.error(f"Link {epanet_node} is not a Pump - cannot apply SCADA boundary")
                return False
            
            # Pump flow control - TODO: implement properly
            # For now, just log
            if boundary_records:
                first_record = boundary_records[0]
                flow = first_record.get('flow')
                if flow is not None:
                    logger.info(f"SCADA flow {flow} L/s for pump {epanet_node} - pump control not yet implemented")
                    # TODO: Implement pump flow control
            
            return False  # Not implemented yet
            
        except Exception as e:
            logger.error(f"Error applying pump boundary for {epanet_node}: {e}")
            return False


# Global service instance
scada_boundary_service = SCADABoundaryService()

