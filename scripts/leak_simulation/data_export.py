"""
Module xuất dữ liệu kết quả mô phỏng ra Parquet và CSV
"""
import os
import pandas as pd
from typing import Dict, List, Any
from pathlib import Path
from utils.logger import logger


class DataExporter:
    """Class để xuất dữ liệu mô phỏng"""
    
    def __init__(
        self,
        output_dir: str,
        timeseries_format: str = "parquet",
        parquet_compression: str = "snappy"
    ):
        """
        Args:
            output_dir: Thư mục output
            timeseries_format: 'parquet' hoặc 'csv'
            parquet_compression: Compression cho Parquet
        """
        self.output_dir = Path(output_dir)
        self.timeseries_format = timeseries_format
        self.parquet_compression = parquet_compression
        
        # Tạo thư mục output
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Khởi tạo DataExporter, output: {self.output_dir}")
    
    def export_scenario(
        self,
        scenario_id: int,
        simulation_results: Dict[str, Any],
        scenario_metadata: Dict[str, Any]
    ):
        """
        Xuất kết quả một kịch bản
        
        Args:
            scenario_id: ID kịch bản
            simulation_results: Kết quả mô phỏng
            scenario_metadata: Metadata của kịch bản
        """
        # Tạo thư mục cho scenario
        scenario_dir = self.output_dir / f"scenario_{scenario_id:05d}"
        scenario_dir.mkdir(exist_ok=True)
        
        # Xuất dữ liệu nodes
        self._export_nodes(scenario_dir, scenario_id, simulation_results.get('nodes', {}))
        
        # Xuất dữ liệu pipes
        self._export_pipes(scenario_dir, scenario_id, simulation_results.get('pipes', {}))
        
        logger.info(f"Đã xuất kết quả scenario {scenario_id} vào {scenario_dir}")
    
    def _export_nodes(self, scenario_dir: Path, scenario_id: int, nodes_data: Dict[str, List[Dict]]):
        """Xuất dữ liệu nodes"""
        all_records = []
        
        for node_name, node_records in nodes_data.items():
            for record in node_records:
                record_copy = record.copy()
                record_copy['node_id'] = node_name
                record_copy['scenario_id'] = scenario_id
                all_records.append(record_copy)
        
        if not all_records:
            return
        
        df = pd.DataFrame(all_records)
        
        # Sắp xếp theo timestamp và node_id
        df = df.sort_values(['timestamp', 'node_id'])
        
        # Xuất file
        if self.timeseries_format == "parquet":
            output_file = scenario_dir / "nodes.parquet"
            df.to_parquet(output_file, compression=self.parquet_compression, index=False)
        else:
            output_file = scenario_dir / "nodes.csv"
            df.to_csv(output_file, index=False)
        
        logger.debug(f"Đã xuất {len(df)} records nodes cho scenario {scenario_id}")
    
    def _export_pipes(self, scenario_dir: Path, scenario_id: int, pipes_data: Dict[str, List[Dict]]):
        """Xuất dữ liệu pipes"""
        all_records = []
        
        for pipe_name, pipe_records in pipes_data.items():
            for record in pipe_records:
                record_copy = record.copy()
                record_copy['pipe_id'] = pipe_name
                record_copy['scenario_id'] = scenario_id
                all_records.append(record_copy)
        
        if not all_records:
            return
        
        df = pd.DataFrame(all_records)
        
        # Sắp xếp theo timestamp và pipe_id
        df = df.sort_values(['timestamp', 'pipe_id'])
        
        # Xuất file
        if self.timeseries_format == "parquet":
            output_file = scenario_dir / "pipes.parquet"
            df.to_parquet(output_file, compression=self.parquet_compression, index=False)
        else:
            output_file = scenario_dir / "pipes.csv"
            df.to_csv(output_file, index=False)
        
        logger.debug(f"Đã xuất {len(df)} records pipes cho scenario {scenario_id}")
    
    def export_metadata(self, scenarios: List[Dict[str, Any]]):
        """
        Xuất file metadata.csv chứa thông tin tất cả kịch bản
        
        Args:
            scenarios: Danh sách metadata các kịch bản
        """
        if not scenarios:
            return
        
        df = pd.DataFrame(scenarios)
        
        # Sắp xếp theo scenario_id
        df = df.sort_values('scenario_id')
        
        output_file = self.output_dir / "metadata.csv"
        df.to_csv(output_file, index=False)
        
        logger.info(f"Đã xuất metadata cho {len(scenarios)} kịch bản vào {output_file}")
    
    def export_labels(self, scenarios: List[Dict[str, Any]]):
        """
        Xuất file labels.csv cho training ML
        
        Args:
            scenarios: Danh sách metadata các kịch bản
        """
        if not scenarios:
            return
        
        # Tạo labels: mỗi scenario có leak hay không, tại node nào
        # SUPPORT MULTIPLE LEAKS PER SCENARIO
        labels = []
        for scenario in scenarios:
            # Check if scenario has multiple leaks (new format)
            if 'n_leaks' in scenario and scenario['n_leaks'] > 1:
                # Parse multiple leaks
                import ast
                leak_nodes = ast.literal_eval(scenario['leak_nodes']) if isinstance(scenario['leak_nodes'], str) else scenario['leak_nodes']
                leak_areas = ast.literal_eval(scenario['leak_areas_m2']) if isinstance(scenario['leak_areas_m2'], str) else scenario['leak_areas_m2']
                leak_starts = ast.literal_eval(scenario['leak_start_times_s']) if isinstance(scenario['leak_start_times_s'], str) else scenario['leak_start_times_s']
                leak_durations = ast.literal_eval(scenario['leak_durations_s']) if isinstance(scenario['leak_durations_s'], str) else scenario['leak_durations_s']
                leak_ends = ast.literal_eval(scenario['leak_end_times_s']) if isinstance(scenario['leak_end_times_s'], str) else scenario['leak_end_times_s']
                
                # Create one label per leak
                for i in range(len(leak_nodes)):
                    label = {
                        'scenario_id': scenario['scenario_id'],
                        'has_leak': True,
                        'leak_node': leak_nodes[i],
                        'leak_area_m2': leak_areas[i],
                        'leak_start_time_s': leak_starts[i],
                        'leak_duration_s': leak_durations[i],
                        'leak_end_time_s': leak_ends[i],
                        'leak_start_time_h': leak_starts[i] / 3600.0,
                        'leak_duration_h': leak_durations[i] / 3600.0,
                        'leak_end_time_h': leak_ends[i] / 3600.0,
                        'discharge_coeff': scenario.get('discharge_coeff', 0.75)
                    }
                    labels.append(label)
            else:
                # Single leak (old format or n_leaks=1)
                label = {
                    'scenario_id': scenario['scenario_id'],
                    'has_leak': True,
                    'leak_node': scenario['leak_node'],
                    'leak_area_m2': scenario['leak_area_m2'],
                    'leak_start_time_s': scenario['start_time_s'],
                    'leak_duration_s': scenario['duration_s'],
                    'leak_end_time_s': scenario['end_time_s'],
                    'leak_start_time_h': scenario['start_time_h'],
                    'leak_duration_h': scenario['duration_h'],
                    'leak_end_time_h': scenario['end_time_h'],
                    'discharge_coeff': scenario['discharge_coeff']
                }
                labels.append(label)
        
        df = pd.DataFrame(labels)
        
        # Sắp xếp theo scenario_id, leak_start_time_s
        df = df.sort_values(['scenario_id', 'leak_start_time_s'])
        
        output_file = self.output_dir / "labels.csv"
        df.to_csv(output_file, index=False)
        
        logger.info(f"Đã xuất labels cho {len(labels)} leaks từ {df['scenario_id'].nunique()} kịch bản vào {output_file}")

