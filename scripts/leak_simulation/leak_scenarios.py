"""
Module sinh kịch bản rò rỉ
"""
import random
import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass
from utils.logger import logger


@dataclass
class LeakScenario:
    """Một kịch bản rò rỉ"""
    scenario_id: int
    leak_node: str              # Node có rò rỉ (primary leak node, backward compat)
    leak_area_m2: float         # Diện tích lỗ rò (m²) (primary leak)
    start_time_s: int           # Thời gian bắt đầu (giây) (primary leak)
    duration_s: int             # Thời lượng (giây) (primary leak)
    end_time_s: int             # Thời gian kết thúc (giây) (primary leak)
    discharge_coeff: float      # Hệ số xả Cd
    
    # NEW: Support for multiple leaks per scenario
    leak_nodes: Optional[List[str]] = None              # List of all leak nodes (including primary)
    leak_areas_m2: Optional[List[float]] = None         # List of all leak areas
    leak_start_times_s: Optional[List[int]] = None      # List of all start times
    leak_durations_s: Optional[List[int]] = None        # List of all durations
    leak_end_times_s: Optional[List[int]] = None        # List of all end times
    
    def to_dict(self) -> Dict:
        """Chuyển thành dictionary"""
        result = {
            'scenario_id': self.scenario_id,
            'leak_node': self.leak_node,  # Primary leak node (for backward compat)
            'leak_area_m2': self.leak_area_m2,
            'start_time_s': self.start_time_s,
            'duration_s': self.duration_s,
            'end_time_s': self.end_time_s,
            'start_time_h': self.start_time_s / 3600.0,
            'duration_h': self.duration_s / 3600.0,
            'end_time_h': self.end_time_s / 3600.0,
            'discharge_coeff': self.discharge_coeff
        }
        
        # Add multi-leak info if available
        if self.leak_nodes:
            result['leak_nodes'] = self.leak_nodes
            result['leak_areas_m2'] = self.leak_areas_m2
            result['leak_start_times_s'] = self.leak_start_times_s
            result['leak_durations_s'] = self.leak_durations_s
            result['leak_end_times_s'] = self.leak_end_times_s
            result['n_leaks'] = len(self.leak_nodes)
        
        return result


class LeakScenarioGenerator:
    """Generator để tạo các kịch bản rò rỉ"""
    
    def __init__(
        self,
        leak_nodes: List[str],
        leak_area_range: Dict[str, float],
        leak_time_range: Dict[str, float],
        discharge_coeff: float,
        leaks_per_scenario: int = 1
    ):
        """
        Args:
            leak_nodes: Danh sách nodes có thể có rò rỉ
            leak_area_range: {'min': float, 'max': float} (m²)
            leak_time_range: {'start_h_min': float, 'start_h_max': float, 
                             'duration_h_min': float, 'duration_h_max': float}
            discharge_coeff: Hệ số xả Cd
            leaks_per_scenario: Số lượng leaks đồng thời per scenario (default: 1)
        """
        self.leak_nodes = leak_nodes
        self.leak_area_range = leak_area_range
        self.leak_time_range = leak_time_range
        self.discharge_coeff = discharge_coeff
        self.leaks_per_scenario = leaks_per_scenario
        
        logger.info(f"Khởi tạo LeakScenarioGenerator với {len(leak_nodes)} nodes")
        logger.info(f"Leaks per scenario: {leaks_per_scenario}")
    
    def generate(self, n_scenarios: int, simulation_duration_h: float, 
                 ensure_all_nodes: bool = False) -> List[LeakScenario]:
        """
        Sinh n_scenarios kịch bản rò rỉ
        
        Args:
            n_scenarios: Số lượng kịch bản
            simulation_duration_h: Thời gian mô phỏng (giờ)
            ensure_all_nodes: Nếu True, đảm bảo mỗi node có ít nhất 1 scenario
        
        Returns:
            Danh sách kịch bản
        """
        scenarios = []
        used_nodes = set()
        
        # Nếu ensure_all_nodes, đảm bảo mỗi node có ít nhất 1 scenario
        if ensure_all_nodes:
            if n_scenarios < len(self.leak_nodes):
                logger.warning(
                    f"n_scenarios ({n_scenarios}) < số nodes ({len(self.leak_nodes)}). "
                    f"Sẽ tạo {len(self.leak_nodes)} scenarios để cover hết nodes."
                )
                n_scenarios = len(self.leak_nodes)
            
            # Phase 1: Tạo 1 scenario cho mỗi node
            node_list = list(self.leak_nodes)
            random.shuffle(node_list)
            for i, leak_node in enumerate(node_list[:n_scenarios]):
                used_nodes.add(leak_node)
                scenario = self._create_scenario(i + 1, leak_node, simulation_duration_h)
                scenarios.append(scenario)
        
        # Phase 2: Tạo các scenarios ngẫu nhiên cho số còn lại
        remaining = n_scenarios - len(scenarios)
        for i in range(remaining):
            scenario_id = len(scenarios) + 1
            # Chọn node ngẫu nhiên
            leak_node = random.choice(self.leak_nodes)
            scenario = self._create_scenario(scenario_id, leak_node, simulation_duration_h)
            scenarios.append(scenario)
        
        logger.info(f"Đã sinh {len(scenarios)} kịch bản rò rỉ")
        if ensure_all_nodes:
            unique_nodes = len(set(s.leak_node for s in scenarios))
            logger.info(f"Coverage: {unique_nodes}/{len(self.leak_nodes)} nodes ({unique_nodes/len(self.leak_nodes)*100:.1f}%)")
        
        return scenarios
    
    def _create_scenario(self, scenario_id: int, leak_node: str, 
                        simulation_duration_h: float) -> LeakScenario:
        """
        Tạo một scenario với node và tham số ngẫu nhiên.
        Nếu leaks_per_scenario > 1, tạo multiple leaks đồng thời.
        """
        if self.leaks_per_scenario == 1:
            # Single leak (backward compatible)
            leak_area = self._sample_log_uniform(
                self.leak_area_range['min'],
                self.leak_area_range['max']
            )
            
            start_h = random.uniform(
                self.leak_time_range['start_h_min'],
                min(self.leak_time_range['start_h_max'], simulation_duration_h - 1)
            )
            
            max_duration = min(
                self.leak_time_range['duration_h_max'],
                simulation_duration_h - start_h
            )
            duration_h = random.uniform(
                self.leak_time_range['duration_h_min'],
                max_duration
            )
            
            start_time_s = int(start_h * 3600)
            duration_s = int(duration_h * 3600)
            end_time_s = start_time_s + duration_s
            
            return LeakScenario(
                scenario_id=scenario_id,
                leak_node=leak_node,
                leak_area_m2=leak_area,
                start_time_s=start_time_s,
                duration_s=duration_s,
                end_time_s=end_time_s,
                discharge_coeff=self.discharge_coeff
            )
        else:
            # Multiple leaks per scenario
            # Select N unique nodes (including the primary node)
            available_nodes = [n for n in self.leak_nodes if n != leak_node]
            n_additional = min(self.leaks_per_scenario - 1, len(available_nodes))
            additional_nodes = random.sample(available_nodes, n_additional) if n_additional > 0 else []
            all_leak_nodes = [leak_node] + additional_nodes
            
            # Generate parameters for each leak
            leak_areas = []
            start_times_s = []
            durations_s = []
            end_times_s = []
            
            for _ in all_leak_nodes:
                leak_area = self._sample_log_uniform(
                    self.leak_area_range['min'],
                    self.leak_area_range['max']
                )
                
                start_h = random.uniform(
                    self.leak_time_range['start_h_min'],
                    min(self.leak_time_range['start_h_max'], simulation_duration_h - 1)
                )
                
                max_duration = min(
                    self.leak_time_range['duration_h_max'],
                    simulation_duration_h - start_h
                )
                duration_h = random.uniform(
                    self.leak_time_range['duration_h_min'],
                    max_duration
                )
                
                start_time_s = int(start_h * 3600)
                duration_s_val = int(duration_h * 3600)
                end_time_s = start_time_s + duration_s_val
                
                leak_areas.append(leak_area)
                start_times_s.append(start_time_s)
                durations_s.append(duration_s_val)
                end_times_s.append(end_time_s)
            
            # Primary leak is the first one (for backward compat)
            return LeakScenario(
                scenario_id=scenario_id,
                leak_node=all_leak_nodes[0],
                leak_area_m2=leak_areas[0],
                start_time_s=start_times_s[0],
                duration_s=durations_s[0],
                end_time_s=end_times_s[0],
                discharge_coeff=self.discharge_coeff,
                leak_nodes=all_leak_nodes,
                leak_areas_m2=leak_areas,
                leak_start_times_s=start_times_s,
                leak_durations_s=durations_s,
                leak_end_times_s=end_times_s
            )
    
    def generate_old(self, n_scenarios: int, simulation_duration_h: float) -> List[LeakScenario]:
        """
        DEPRECATED: Dùng generate() với ensure_all_nodes=False
        """
        return self.generate(n_scenarios, simulation_duration_h, ensure_all_nodes=False)
        
        # Code cũ giữ lại để reference
        for i in range(n_scenarios):
            # Chọn node ngẫu nhiên
            leak_node = random.choice(self.leak_nodes)
            
            # Bốc thăm diện tích lỗ rò (log-uniform distribution)
            leak_area = self._sample_log_uniform(
                self.leak_area_range['min'],
                self.leak_area_range['max']
            )
            
            # Bốc thăm thời gian bắt đầu (giờ)
            start_h = random.uniform(
                self.leak_time_range['start_h_min'],
                min(self.leak_time_range['start_h_max'], simulation_duration_h - 1)
            )
            
            # Bốc thăm thời lượng (giờ)
            max_duration = min(
                self.leak_time_range['duration_h_max'],
                simulation_duration_h - start_h
            )
            duration_h = random.uniform(
                self.leak_time_range['duration_h_min'],
                max_duration
            )
            
            # Chuyển sang giây
            start_time_s = int(start_h * 3600)
            duration_s = int(duration_h * 3600)
            end_time_s = start_time_s + duration_s
            
            scenario = LeakScenario(
                scenario_id=i + 1,
                leak_node=leak_node,
                leak_area_m2=leak_area,
                start_time_s=start_time_s,
                duration_s=duration_s,
                end_time_s=end_time_s,
                discharge_coeff=self.discharge_coeff
            )
            
            scenarios.append(scenario)
        
        logger.info(f"Đã sinh {len(scenarios)} kịch bản rò rỉ")
        return scenarios
    
    def _sample_log_uniform(self, min_val: float, max_val: float) -> float:
        """
        Bốc thăm từ phân phối log-uniform
        P(x) ∝ 1/x trong khoảng [min, max]
        """
        if min_val <= 0 or max_val <= 0:
            raise ValueError("min và max phải > 0 cho log-uniform")
        
        # Log-uniform: log(x) ~ Uniform(log(min), log(max))
        log_min = np.log(min_val)
        log_max = np.log(max_val)
        log_sample = random.uniform(log_min, log_max)
        return np.exp(log_sample)

