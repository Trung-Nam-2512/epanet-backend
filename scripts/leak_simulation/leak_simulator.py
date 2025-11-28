"""
Module chạy mô phỏng rò rỉ với WNTR
"""
import wntr
import wntr.network.elements
import numpy as np
from typing import Dict, Any, Optional
from scripts.leak_simulation.leak_scenarios import LeakScenario
from scripts.leak_simulation.load_model import ModelLoader
from utils.logger import logger


class LeakSimulator:
    """Class để chạy mô phỏng rò rỉ"""
    
    def __init__(
        self,
        model_loader: ModelLoader,
        duration_h: float,
        hydraulic_timestep_h: float,
        report_timestep_h: float
    ):
        """
        Args:
            model_loader: ModelLoader đã nạp mô hình
            duration_h: Thời gian mô phỏng (giờ)
            hydraulic_timestep_h: Bước thời gian thủy lực (giờ)
            report_timestep_h: Bước thời gian báo cáo (giờ)
        """
        self.model_loader = model_loader
        self.duration_h = duration_h
        self.hydraulic_timestep_h = hydraulic_timestep_h
        self.report_timestep_h = report_timestep_h
    
    def run_scenario(self, scenario: LeakScenario) -> Dict[str, Any]:
        """
        Chạy một kịch bản rò rỉ
        
        Args:
            scenario: Kịch bản rò rỉ
            
        Returns:
            Dict chứa kết quả mô phỏng
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
            
            # Set pattern multipliers to 1.0 (fixed demand)
            for pattern_id in wn.pattern_name_list:
                pattern = wn.get_pattern(pattern_id)
                pattern.multipliers = [1.0] * len(pattern.multipliers)
            
            # Thêm rò rỉ vào node(s)
            # Check if scenario has multiple leaks
            if scenario.leak_nodes and len(scenario.leak_nodes) > 1:
                # Multiple leaks per scenario
                for i, leak_node in enumerate(scenario.leak_nodes):
                    junction = wn.get_node(leak_node)
                    if not isinstance(junction, wntr.network.elements.Junction):
                        logger.warning(f"Node {leak_node} không phải là junction, bỏ qua")
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
                        f"tại node {leak_node}, diện tích {scenario.leak_areas_m2[i]:.6f} m², "
                        f"từ {scenario.leak_start_times_s[i]}s đến {scenario.leak_end_times_s[i]}s"
                    )
            else:
                # Single leak (backward compatible)
                junction = wn.get_node(scenario.leak_node)
                if not isinstance(junction, wntr.network.elements.Junction):
                    raise ValueError(f"Node {scenario.leak_node} không phải là junction")
                
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
            
            # Trích xuất kết quả
            simulation_results = self._extract_results(results, scenario)
            
            return {
                'success': True,
                'scenario_id': scenario.scenario_id,
                'results': simulation_results
            }
            
        except Exception as e:
            error_msg = f"Lỗi khi chạy scenario {scenario.scenario_id}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'scenario_id': scenario.scenario_id,
                'error': error_msg,
                'results': None
            }
    
    def _extract_results(self, results, scenario: LeakScenario) -> Dict[str, Any]:
        """
        Trích xuất kết quả từ WNTR
        
        Returns:
            Dict chứa time-series data cho tất cả nodes và links
        """
        try:
            # Trích xuất kết quả nodes
            node_results = {}
            if hasattr(results, 'node'):
                # Normalize leak nodes for comparison (handle both "1359.0" and "1359")
                leak_node_list = []
                if scenario.leak_nodes:
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
                g = 9.81  # m/s² (gia tốc trọng trường)
                
                for node_name in results.node['pressure'].columns:
                    # Normalize node_name từ WNTR (có thể là số hoặc string)
                    node_name_str = str(node_name).strip()
                    try:
                        if '.' in node_name_str:
                            node_name_normalized = str(int(float(node_name_str)))
                        else:
                            node_name_normalized = node_name_str
                    except:
                        node_name_normalized = node_name_str
                    
                    # Check if this node is a leak node
                    is_leak_node = (node_name_normalized in leak_node_list)
                    
                    node_data = []
                    for time_idx, timestamp in enumerate(results.node['pressure'].index):
                        # Đảm bảo timestamp là số (seconds)
                        timestamp_sec = float(timestamp) if timestamp is not None else 0.0
                        
                        pressure = results.node['pressure'].loc[timestamp, node_name]
                        head = results.node['head'].loc[timestamp, node_name]
                        demand = results.node['demand'].loc[timestamp, node_name]
                        
                        # Lấy leak demand nếu có từ WNTR (hỗ trợ multiple leaks)
                        leak_demand = 0.0
                        if 'leak_demand' in results.node:
                            if is_leak_node:
                                try:
                                    leak_demand_val = results.node['leak_demand'].loc[timestamp, node_name]
                                    if leak_demand_val is not None and not np.isnan(leak_demand_val):
                                        leak_demand = float(leak_demand_val)
                                except (KeyError, IndexError, AttributeError):
                                    leak_demand = 0.0
                        
                        # Nếu không có từ WNTR hoặc = 0, tính thủ công từ công thức vật lý
                        # Chỉ tính nếu đây là leak node VÀ leak đang hoạt động
                        if leak_demand == 0.0 and is_leak_node:
                            # Kiểm tra xem leak có đang hoạt động không
                            in_leak_time = False
                            
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
                        
                        # Convert demand từ m³/s sang L/s
                        demand_lps = demand * 1000 if demand is not None else 0.0
                        leak_demand_lps = leak_demand * 1000 if leak_demand is not None else 0.0
                        
                        node_data.append({
                            'timestamp': timestamp,
                            'pressure': float(pressure) if pressure is not None else 0.0,
                            'head': float(head) if head is not None else 0.0,
                            'demand': float(demand_lps),
                            'leak_demand': float(leak_demand_lps)
                        })
                    
                    node_results[node_name] = node_data
            
            # Trích xuất kết quả pipes
            pipe_results = {}
            if hasattr(results, 'link'):
                for pipe_name in results.link['flowrate'].columns:
                    pipe_data = []
                    for timestamp in results.link['flowrate'].index:
                        flow = results.link['flowrate'].loc[timestamp, pipe_name]
                        flow_lps = flow * 1000 if flow is not None else 0.0  # m³/s -> L/s
                        
                        pipe_data.append({
                            'timestamp': timestamp,
                            'flow': float(flow_lps)
                        })
                    
                    pipe_results[pipe_name] = pipe_data
            
            return {
                'nodes': node_results,
                'pipes': pipe_results,
                'timestamps': list(results.node['pressure'].index) if hasattr(results, 'node') else []
            }
            
        except Exception as e:
            logger.error(f"Lỗi khi trích xuất kết quả: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'nodes': {},
                'pipes': {},
                'timestamps': []
            }


def run_scenario_worker(args):
    """
    Worker function để chạy song song (phải ở module level để pickle được)
    
    Lưu kết quả ra file ngay trong worker để tránh MemoryError khi serialize qua queue.
    Chỉ trả về metadata nhỏ.
    
    Args:
        args: Tuple (scenario_dict, model_path, sim_config, output_dir, export_config, noise_config)
    
    Returns:
        Dict chỉ chứa metadata nhỏ (không có simulation_results lớn)
    """
    import wntr
    from pathlib import Path
    from scripts.leak_simulation.leak_scenarios import LeakScenario
    from scripts.leak_simulation.load_model import ModelLoader
    from scripts.leak_simulation.data_export import DataExporter
    from scripts.leak_simulation.noise_injection import NoiseInjector
    
    scenario_dict, model_path, sim_config, output_dir, export_config, noise_config = args
    
    # Tạo lại scenario object (hỗ trợ cả single và multiple leaks)
    if 'leak_nodes' in scenario_dict and scenario_dict.get('leak_nodes'):
        # Multiple leaks
        scenario = LeakScenario(
            scenario_id=scenario_dict['scenario_id'],
            leak_node=scenario_dict['leak_node'],
            leak_area_m2=scenario_dict['leak_area_m2'],
            start_time_s=scenario_dict['start_time_s'],
            duration_s=scenario_dict['duration_s'],
            end_time_s=scenario_dict['end_time_s'],
            discharge_coeff=scenario_dict['discharge_coeff'],
            leak_nodes=scenario_dict.get('leak_nodes'),
            leak_areas_m2=scenario_dict.get('leak_areas_m2'),
            leak_start_times_s=scenario_dict.get('leak_start_times_s'),
            leak_durations_s=scenario_dict.get('leak_durations_s'),
            leak_end_times_s=scenario_dict.get('leak_end_times_s')
        )
    else:
        # Single leak (backward compatible)
        scenario = LeakScenario(
            scenario_id=scenario_dict['scenario_id'],
            leak_node=scenario_dict['leak_node'],
            leak_area_m2=scenario_dict['leak_area_m2'],
            start_time_s=scenario_dict['start_time_s'],
            duration_s=scenario_dict['duration_s'],
            end_time_s=scenario_dict['end_time_s'],
            discharge_coeff=scenario_dict['discharge_coeff']
        )
    
    # Tạo model loader và simulator
    model_loader = ModelLoader(model_path)
    success, _ = model_loader.load_and_validate()
    if not success:
        return {
            'success': False,
            'scenario_id': scenario.scenario_id,
            'error': 'Không thể nạp mô hình',
            'metadata': scenario.to_dict()
        }
    
    simulator = LeakSimulator(
        model_loader=model_loader,
        duration_h=sim_config['duration_h'],
        hydraulic_timestep_h=sim_config['hydraulic_timestep_h'],
        report_timestep_h=sim_config['report_timestep_h']
    )
    
    # Chạy mô phỏng
    result = simulator.run_scenario(scenario)
    
    if not result.get('success', False):
        return {
            'success': False,
            'scenario_id': scenario.scenario_id,
            'error': result.get('error', 'Unknown error'),
            'metadata': scenario.to_dict()
        }
    
    # Lưu kết quả ra file ngay trong worker (tránh serialize qua queue)
    try:
        # Thêm nhiễu nếu được bật
        noisy_results = result['results']
        if noise_config:
            noise_injector = NoiseInjector(
                pressure_sigma=noise_config.get('pressure_sigma', 0.0),
                flow_sigma=noise_config.get('flow_sigma', 0.0),
                enabled=noise_config.get('enabled', False)
            )
            noisy_results = noise_injector.inject_noise(result['results'])
        
        exporter = DataExporter(
            output_dir=output_dir,
            timeseries_format=export_config.get('timeseries_format', 'parquet'),
            parquet_compression=export_config.get('parquet_compression', 'snappy')
        )
        
        exporter.export_scenario(
            scenario_id=scenario.scenario_id,
            simulation_results=noisy_results,
            scenario_metadata=scenario.to_dict()
        )
        
        # Chỉ trả về metadata nhỏ (không có simulation_results)
        return {
            'success': True,
            'scenario_id': scenario.scenario_id,
            'metadata': scenario.to_dict()
        }
    except Exception as e:
        return {
            'success': False,
            'scenario_id': scenario.scenario_id,
            'error': f'Lỗi khi xuất file: {str(e)}',
            'metadata': scenario.to_dict()
        }

