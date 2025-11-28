"""
Module chạy mô phỏng một scenario rò rỉ và xuất kết quả
Tuân theo nguyên tắc Single Responsibility - chỉ chịu trách nhiệm chạy 1 scenario
"""
import wntr
import wntr.network.elements
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional
from scripts.leak_simulation.leak_scenarios import LeakScenario
from scripts.leak_simulation.load_model import ModelLoader
from scripts.leak_simulation.scada_boundary import SCADABoundaryCondition
from utils.logger import logger


class Simulation:
    """Class để chạy mô phỏng một scenario rò rỉ"""
    
    def __init__(
        self,
        model_loader: ModelLoader,
        duration_h: float,
        hydraulic_timestep_h: float,
        report_timestep_h: float,
        use_scada: bool = True
    ):
        """
        Args:
            model_loader: ModelLoader đã nạp mô hình
            duration_h: Thời gian mô phỏng (giờ)
            hydraulic_timestep_h: Bước thời gian thủy lực (giờ)
            report_timestep_h: Bước thời gian báo cáo (giờ)
            use_scada: Có sử dụng SCADA data thật không
        """
        self.model_loader = model_loader
        self.duration_h = duration_h
        self.hydraulic_timestep_h = hydraulic_timestep_h
        self.report_timestep_h = report_timestep_h
        self.use_scada = use_scada
        self.scada_boundary = SCADABoundaryCondition(use_scada=use_scada) if use_scada else None
    
    def run(self, scenario: LeakScenario) -> pd.DataFrame:
        """
        Chạy một kịch bản rò rỉ và trả về DataFrame với format chuẩn
        
        Args:
            scenario: Kịch bản rò rỉ
            
        Returns:
            DataFrame với columns: timestamp, node_id, pressure, head, demand, 
            leak_demand, scenario_id, leak_node
        """
        try:
            # Tạo bản sao mô hình (tránh đụng độ khi chạy song song)
            wn = self.model_loader.create_model_copy()
            if not wn:
                raise ValueError("Không thể tạo bản sao mô hình")
            
            # Cấu hình thời gian mô phỏng
            wn.options.time.duration = int(self.duration_h * 3600)  # Giây
            wn.options.time.hydraulic_timestep = int(self.hydraulic_timestep_h * 3600)
            wn.options.time.report_timestep = int(self.report_timestep_h * 3600)
            
            # Set pattern multipliers to 1.0 (fixed demand) - đủ cho ML training
            # Note: Demand pattern từ INP sẽ bị override để có demand cố định
            logger.info("Using fixed demand (pattern multipliers = 1.0) for ML training")
            for pattern_id in wn.pattern_name_list:
                pattern = wn.get_pattern(pattern_id)
                pattern.multipliers = [1.0] * len(pattern.multipliers)
            
            # Load và apply SCADA data thật làm boundary conditions (reservoir/tank/pump)
            # SCADA chỉ dùng cho boundary conditions, KHÔNG dùng cho demand
            if self.use_scada and self.scada_boundary:
                try:
                    scada_data = self.scada_boundary.load_scada_data(hours_back=int(self.duration_h))
                    if scada_data:
                        scada_applied = self.scada_boundary.apply_to_wntr(wn, scada_data)
                        if scada_applied:
                            logger.info("Applied SCADA real-time data as boundary conditions")
                        else:
                            logger.info("SCADA data loaded but not applied - using INP boundary conditions")
                    else:
                        logger.info("No SCADA data available - using INP boundary conditions")
                except Exception as e:
                    logger.warning(f"Error loading/applying SCADA data: {e} - using INP boundary conditions")
            
            # Thêm rò rỉ vào node(s)
            # Fix: Hỗ trợ multiple leaks per scenario
            if scenario.leak_nodes and len(scenario.leak_nodes) > 1:
                # Multiple leaks per scenario
                for i, leak_node_raw in enumerate(scenario.leak_nodes):
                    leak_node_normalized = str(int(float(leak_node_raw))) if '.' in str(leak_node_raw) else str(leak_node_raw)
                    junction = wn.get_node(leak_node_normalized)
                    if not isinstance(junction, wntr.network.elements.Junction):
                        logger.warning(f"Node {leak_node_normalized} không phải là junction, bỏ qua")
                        continue
                    
                    junction.add_leak(
                        wn,
                        area=scenario.leak_areas_m2[i],
                        discharge_coeff=scenario.discharge_coeff,
                        start_time=scenario.leak_start_times_s[i],
                        end_time=scenario.leak_end_times_s[i]
                    )
                    
                    logger.info(
                        f"Scenario {scenario.scenario_id}: Leak {i+1}/{len(scenario.leak_nodes)} "
                        f"tại node {leak_node_normalized}, diện tích {scenario.leak_areas_m2[i]:.6f} m², "
                        f"từ {scenario.leak_start_times_s[i]}s đến {scenario.leak_end_times_s[i]}s"
                    )
            else:
                # Single leak (backward compatible)
                leak_node_normalized = str(int(float(scenario.leak_node))) if '.' in str(scenario.leak_node) else str(scenario.leak_node)
                junction = wn.get_node(leak_node_normalized)
                if not isinstance(junction, wntr.network.elements.Junction):
                    raise ValueError(f"Node {leak_node_normalized} không phải là junction")
                
                junction.add_leak(
                    wn,
                    area=scenario.leak_area_m2,
                    discharge_coeff=scenario.discharge_coeff,
                    start_time=scenario.start_time_s,
                    end_time=scenario.end_time_s
                )
                
                logger.info(
                    f"Scenario {scenario.scenario_id}: Rò rỉ tại node {scenario.leak_node}, "
                    f"diện tích {scenario.leak_area_m2:.6f} m², "
                    f"từ {scenario.start_time_s}s đến {scenario.end_time_s}s"
                )
            
            # Chạy mô phỏng
            sim = wntr.sim.WNTRSimulator(wn)
            results = sim.run_sim()
            
            # Trích xuất và format kết quả
            df = self._extract_to_dataframe(results, scenario)
            
            return df
            
        except Exception as e:
            error_msg = f"Lỗi khi chạy scenario {scenario.scenario_id}: {str(e)}"
            logger.error(error_msg)
            import traceback
            logger.error(traceback.format_exc())
            raise RuntimeError(error_msg)
    
    def _extract_to_dataframe(self, results, scenario: LeakScenario) -> pd.DataFrame:
        """
        Trích xuất kết quả từ WNTR và format thành DataFrame
        
        Returns:
            DataFrame với format: timestamp, node_id, pressure, head, demand, 
            leak_demand, scenario_id, leak_node
        """
        records = []
        
        try:
            if not hasattr(results, 'node'):
                raise ValueError("Kết quả không có dữ liệu nodes")
            
            # Lấy timestamps
            timestamps = results.node['pressure'].index
            
            # Lấy tất cả node names và normalize về string
            # WNTR có thể trả về mixed types (int, float, string)
            node_names_raw = results.node['pressure'].columns
            node_names = [str(name) for name in node_names_raw]
            
            # Normalize leak nodes for comparison (handle both "1359.0" and "1359", support multiple leaks)
            leak_node_list = []
            if scenario.leak_nodes and len(scenario.leak_nodes) > 1:
                # Multiple leaks
                for ln in scenario.leak_nodes:
                    leak_node_normalized = str(int(float(ln))) if '.' in str(ln) else str(ln)
                    leak_node_list.append(leak_node_normalized)
            else:
                # Single leak (backward compatible)
                leak_node_normalized = str(int(float(scenario.leak_node))) if '.' in str(scenario.leak_node) else str(scenario.leak_node)
                leak_node_list = [leak_node_normalized]
            
            # Tính leak_demand thủ công từ công thức vật lý
            # Q = Cd * A * sqrt(2 * g * h)
            # với h = gauge pressure (pressure, không phải head)
            g = 9.81  # m/s² (gia tốc trọng trường)
            
            # Debug: log leak node info (chỉ lần đầu)
            debug_logged = False
            debug_match_count = 0
            debug_calc_count = 0
            
            logger.debug(f"Looking for leaks at nodes {leak_node_list} "
                        f"(original: {scenario.leak_node if not scenario.leak_nodes else scenario.leak_nodes})")
            
            # Duyệt qua tất cả nodes và timestamps
            for node_name in node_names:
                # Normalize node_name từ WNTR (có thể là số hoặc string)
                node_name_str = str(node_name).strip()
                # Xử lý trường hợp node_name có thể là float từ pandas
                try:
                    if '.' in node_name_str:
                        node_name_normalized = str(int(float(node_name_str)))
                    else:
                        node_name_normalized = node_name_str
                except:
                    node_name_normalized = node_name_str
                
                # Chỉ xử lý logic tính leak_demand nếu đây là leak node
                is_leak_node = (node_name_normalized in leak_node_list)
                
                for timestamp in timestamps:
                    # Đảm bảo timestamp là số (seconds)
                    timestamp_sec = float(timestamp) if timestamp is not None else 0.0
                    
                    # Lấy các giá trị từ kết quả
                    pressure = results.node['pressure'].loc[timestamp, node_name]
                    head = results.node['head'].loc[timestamp, node_name]
                    demand = results.node['demand'].loc[timestamp, node_name]
                    
                    # Tính leak_demand:
                    # 1. Thử lấy từ WNTR results trước
                    leak_demand = 0.0
                    if 'leak_demand' in results.node:
                        try:
                            leak_demand_val = results.node['leak_demand'].loc[timestamp, node_name]
                            if leak_demand_val is not None and not np.isnan(leak_demand_val):
                                leak_demand = float(leak_demand_val)
                        except (KeyError, IndexError, AttributeError):
                            leak_demand = 0.0
                    
                    # 2. Nếu không có từ WNTR hoặc = 0, tính thủ công từ công thức vật lý
                    # Chỉ tính nếu đây là leak node VÀ leak đang hoạt động
                    if leak_demand == 0.0 and is_leak_node:
                        # Kiểm tra xem leak có đang hoạt động không (đảm bảo so sánh số)
                        # WNTR timestamps có thể là seconds từ start (0, 3600, 7200...) hoặc absolute time
                        # Đảm bảo so sánh đúng bằng cách convert cả hai về số
                        in_leak_time = False
                        leak_area = 0.0
                        
                        if scenario.leak_nodes and len(scenario.leak_nodes) > 1:
                            # Multiple leaks: check if this node has an active leak at this timestamp
                            for i, leak_node_raw in enumerate(scenario.leak_nodes):
                                leak_node_norm = str(int(float(leak_node_raw))) if '.' in str(leak_node_raw) else str(leak_node_raw)
                                if node_name_normalized == leak_node_norm:
                                    start_s = scenario.leak_start_times_s[i]
                                    end_s = scenario.leak_end_times_s[i]
                                    if start_s <= timestamp_sec <= end_s:
                                        in_leak_time = True
                                        leak_area = scenario.leak_areas_m2[i]
                                        break
                        else:
                            # Single leak (backward compatible)
                            in_leak_time = (scenario.start_time_s <= timestamp_sec <= scenario.end_time_s)
                            leak_area = scenario.leak_area_m2
                        
                        if in_leak_time:
                            # h = gauge pressure (m) - áp lực tại node
                            h = float(pressure) if pressure is not None and pressure > 0 else 0.0
                            if h > 0:
                                # Công thức: Q = Cd * A * sqrt(2 * g * h)
                                leak_demand = scenario.discharge_coeff * leak_area * np.sqrt(2 * g * h)
                                debug_calc_count += 1
                                
                                # Log lần đầu tiên tính được leak_demand > 0
                                if debug_calc_count == 1:
                                    logger.info(
                                        f"[DEBUG] Calculated leak_demand for scenario {scenario.scenario_id}: "
                                        f"node={node_name_normalized}, timestamp={timestamp_sec}s, "
                                        f"pressure={h:.3f}m, leak_demand={leak_demand*1000:.6f} L/s"
                                    )
                    
                    # Debug log (chỉ lần đầu match leak node)
                    if not debug_logged and is_leak_node:
                        leak_info = scenario.leak_node if not scenario.leak_nodes else scenario.leak_nodes
                        logger.debug(
                            f"Leak node match: '{node_name_normalized}' in {leak_node_list} "
                            f"(original: '{node_name}', type: {type(node_name)}). "
                            f"Timestamp: {timestamp_sec}s (type: {type(timestamp)}), "
                            f"Leak info: {leak_info}"
                        )
                        debug_logged = True
            
                    # Convert từ m³/s sang L/s
                    demand_lps = (demand * 1000) if demand is not None else 0.0
                    leak_demand_lps = (leak_demand * 1000) if leak_demand is not None else 0.0
                    
                    # Tạo record
                    record = {
                        'timestamp': timestamp,
                        'node_id': node_name,
                        'pressure': float(pressure) if pressure is not None else 0.0,
                        'head': float(head) if head is not None else 0.0,
                        'demand': float(demand_lps),
                        'leak_demand': float(leak_demand_lps),
                        'scenario_id': scenario.scenario_id,
                        'leak_node': scenario.leak_node  # Giữ nguyên format từ metadata
                    }
                    records.append(record)
            
            # Tạo DataFrame
            df = pd.DataFrame(records)
            
            # Sắp xếp theo timestamp và node_id
            df = df.sort_values(['timestamp', 'node_id'])
            
            # Đảm bảo thứ tự cột đúng
            column_order = [
                'timestamp', 'node_id', 'pressure', 'head', 
                'demand', 'leak_demand', 'scenario_id', 'leak_node'
            ]
            df = df[column_order]
            
            logger.debug(
                f"Đã trích xuất {len(df)} records cho scenario {scenario.scenario_id} "
                f"({len(node_names)} nodes, {len(timestamps)} timestamps)"
            )
            
            return df
            
        except Exception as e:
            logger.error(f"Lỗi khi trích xuất kết quả: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            # Trả về DataFrame rỗng với đúng cấu trúc
            return pd.DataFrame(columns=[
                'timestamp', 'node_id', 'pressure', 'head', 
                'demand', 'leak_demand', 'scenario_id', 'leak_node'
            ])

