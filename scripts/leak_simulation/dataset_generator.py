"""
Module sinh và quản lý nhiều scenarios, xuất dataset cho ML training
Tuân theo nguyên tắc Open/Closed - dễ mở rộng cho các loại scenario khác
"""
import os
import sys
import yaml
import multiprocessing as mp
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd

# Thêm đường dẫn project vào path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.leak_simulation.load_model import ModelLoader
from scripts.leak_simulation.leak_scenarios import LeakScenarioGenerator
from scripts.leak_simulation.simulation import Simulation
from utils.logger import logger


class DatasetGenerator:
    """Class để sinh dataset từ nhiều scenarios"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config: Dictionary chứa cấu hình từ YAML
        """
        self.config = config
        self.output_dir = Path(config['out_dir'])
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Nạp mô hình
        inp_path = config['inp_path']
        if not os.path.isabs(inp_path):
            inp_path = str(project_root / inp_path)
        
        self.model_loader = ModelLoader(inp_path)
        success, message = self.model_loader.load_and_validate()
        if not success:
            raise RuntimeError(f"Không thể nạp mô hình: {message}")
        
        logger.info(f"Đã nạp mô hình: {message}")
    
    def generate(self) -> Dict[str, Any]:
        """
        Sinh dataset từ nhiều scenarios
        
        Returns:
            Dict chứa thống kê kết quả
        """
        # 1. Lấy danh sách nodes có thể có rò rỉ
        leak_node_list = self._get_leak_nodes()
        logger.info(f"Sử dụng {len(leak_node_list)} nodes cho rò rỉ")
        
        # 2. Sinh kịch bản
        # Fix: Pass leaks_per_scenario từ config
        leaks_per_scenario = self.config.get('leak_nodes', {}).get('leaks_per_scenario', 1)
        scenario_generator = LeakScenarioGenerator(
            leak_nodes=leak_node_list,
            leak_area_range=self.config['leak_area_m2'],
            leak_time_range=self.config['leak_time_h'],
            discharge_coeff=self.config['discharge_coeff'],
            leaks_per_scenario=leaks_per_scenario  # Fix: Pass leaks_per_scenario
        )
        
        # Check if we should ensure all nodes are covered
        ensure_all_nodes = self.config.get('ensure_all_nodes_covered', False)
        
        scenarios = scenario_generator.generate(
            n_scenarios=self.config['n_scenarios'],
            simulation_duration_h=self.config['simulation']['duration_h'],
            ensure_all_nodes=ensure_all_nodes
        )
        logger.info(f"Đã sinh {len(scenarios)} kịch bản")
        
        # 3. Chạy mô phỏng
        sim_config = self.config['simulation']
        parallel_config = self.config.get('parallel', {})
        use_scada = sim_config.get('use_scada', False)
        
        if parallel_config.get('enabled', True):
            results = self._run_parallel(scenarios, sim_config, parallel_config, use_scada)
        else:
            results = self._run_sequential(scenarios, sim_config, use_scada)
        
        # 4. Xuất kết quả
        successful = sum(1 for r in results if r.get('success', False))
        failed = len(results) - successful
        
        logger.info(f"Kết quả: {successful} thành công, {failed} thất bại")
        
        # Xuất các scenario thành công
        metadata_list = []
        for result in results:
            if not result.get('success', False):
                continue
            
            scenario_id = result['scenario_id']
            df = result['df']
            scenario_meta = result['metadata']
            
            # Lưu file parquet
            output_file = self.output_dir / f"scenario_{scenario_id:05d}.parquet"
            df.to_parquet(
                output_file,
                compression=self.config['export'].get('parquet_compression', 'snappy'),
                index=False
            )
            
            # Lưu CSV nếu được bật
            if self.config['export'].get('save_csv', False):
                csv_file = self.output_dir / f"scenario_{scenario_id:05d}.csv"
                df.to_csv(csv_file, index=False)
            
            metadata_list.append(scenario_meta)
        
        # Xuất metadata
        if metadata_list:
            metadata_df = pd.DataFrame(metadata_list)
            metadata_df = metadata_df.sort_values('scenario_id')
            metadata_file = self.output_dir / "metadata.csv"
            metadata_df.to_csv(metadata_file, index=False)
            logger.info(f"Đã xuất metadata cho {len(metadata_list)} scenarios vào {metadata_file}")
        
        return {
            'total_scenarios': len(scenarios),
            'successful': successful,
            'failed': failed,
            'output_dir': str(self.output_dir)
        }
    
    def _get_leak_nodes(self) -> List[str]:
        """Lấy danh sách nodes có thể có rò rỉ"""
        leak_node_config = self.config.get('leak_nodes', {})
        leak_node_list = leak_node_config.get('node_list')
        
        if not leak_node_list:
            # Dùng tất cả junctions
            return self.model_loader.get_junction_nodes()
        else:
            # Validate nodes
            all_nodes = self.model_loader.get_all_nodes()
            valid_nodes = [n for n in leak_node_list if n in all_nodes]
            if len(valid_nodes) != len(leak_node_list):
                invalid_nodes = set(leak_node_list) - set(valid_nodes)
                logger.warning(f"Có {len(invalid_nodes)} nodes không tồn tại: {invalid_nodes}")
            return valid_nodes
    
    def _run_parallel(
        self, 
        scenarios: List, 
        sim_config: Dict, 
        parallel_config: Dict,
        use_scada: bool = False
    ) -> List[Dict]:
        """Chạy mô phỏng song song"""
        max_workers = parallel_config.get('max_workers')
        if max_workers is None:
            max_workers = mp.cpu_count()
        
        logger.info(f"Chạy song song với {max_workers} workers")
        
        # Chuẩn bị arguments (bao gồm use_scada flag)
        worker_args = [
            (
                scenario.to_dict(),
                self.model_loader.inp_path,
                sim_config,
                use_scada
            )
            for scenario in scenarios
        ]
        
        # Chạy song song - import tại đây để tránh circular import
        from scripts.leak_simulation import dataset_generator
        with mp.Pool(processes=max_workers) as pool:
            results = pool.map(dataset_generator.run_scenario_worker, worker_args)
        
        return results
    
    def _run_sequential(self, scenarios: List, sim_config: Dict, use_scada: bool = False) -> List[Dict]:
        """Chạy mô phỏng tuần tự"""
        logger.info("Chạy tuần tự (không song song)")
        
        simulator = Simulation(
            model_loader=self.model_loader,
            duration_h=sim_config['duration_h'],
            hydraulic_timestep_h=sim_config['hydraulic_timestep_h'],
            report_timestep_h=sim_config['report_timestep_h'],
            use_scada=use_scada
        )
        
        results = []
        for i, scenario in enumerate(scenarios, 1):
            try:
                logger.info(f"Đang chạy scenario {i}/{len(scenarios)}: {scenario.scenario_id}")
                df = simulator.run(scenario)
                
                results.append({
                    'success': True,
                    'scenario_id': scenario.scenario_id,
                    'df': df,
                    'metadata': scenario.to_dict()
                })
            except Exception as e:
                logger.error(f"Scenario {scenario.scenario_id} thất bại: {str(e)}")
                results.append({
                    'success': False,
                    'scenario_id': scenario.scenario_id,
                    'error': str(e)
                })
        
        return results


def run_scenario_worker(args):
    """
    Worker function để chạy song song (phải ở module level để pickle được)
    
    Args:
        args: Tuple (scenario_dict, model_path, sim_config, use_scada)
    
    Returns:
        Dict chứa kết quả mô phỏng
    """
    import wntr
    from scripts.leak_simulation.leak_scenarios import LeakScenario
    from scripts.leak_simulation.load_model import ModelLoader
    from scripts.leak_simulation.simulation import Simulation
    
    scenario_dict, model_path, sim_config, use_scada = args
    
    # Fix: Tạo lại scenario object (hỗ trợ cả single và multiple leaks)
    if 'leak_nodes' in scenario_dict and scenario_dict.get('leak_nodes'):
        # Multiple leaks per scenario
        scenario = LeakScenario(
            scenario_id=scenario_dict['scenario_id'],
            leak_node=scenario_dict['leak_node'],  # Primary leak node
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
        leak_node_raw = scenario_dict['leak_node']
        leak_node_normalized = str(int(float(leak_node_raw))) if '.' in str(leak_node_raw) else str(leak_node_raw)
        scenario = LeakScenario(
            scenario_id=scenario_dict['scenario_id'],
            leak_node=leak_node_normalized,
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
            'error': 'Không thể nạp mô hình'
        }
    
    # use_scada đã được truyền từ args
    
    simulator = Simulation(
        model_loader=model_loader,
        duration_h=sim_config['duration_h'],
        hydraulic_timestep_h=sim_config['hydraulic_timestep_h'],
        report_timestep_h=sim_config['report_timestep_h'],
        use_scada=use_scada
    )
    
    # Chạy mô phỏng
    try:
        df = simulator.run(scenario)
        return {
            'success': True,
            'scenario_id': scenario.scenario_id,
            'df': df,
            'metadata': scenario.to_dict()
        }
    except Exception as e:
        return {
            'success': False,
            'scenario_id': scenario.scenario_id,
            'error': str(e)
        }

