"""
Script chính để sinh và chạy các kịch bản rò rỉ
"""
import os
import sys
import yaml
import multiprocessing as mp
from pathlib import Path
from typing import List, Dict, Any

# Thêm đường dẫn project vào path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.leak_simulation.load_model import ModelLoader
from scripts.leak_simulation.leak_scenarios import LeakScenarioGenerator
from scripts.leak_simulation.leak_simulator import LeakSimulator, run_scenario_worker
from scripts.leak_simulation.noise_injection import NoiseInjector
from scripts.leak_simulation.data_export import DataExporter
from utils.logger import logger


def load_config(config_path: str) -> Dict[str, Any]:
    """Nạp cấu hình từ file YAML"""
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config


def main():
    """Hàm main"""
    # Nạp cấu hình
    config_path = project_root / "config" / "leak_simulation_config.yaml"
    
    if not config_path.exists():
        print(f"Loi: Khong tim thay file cau hinh: {config_path}")
        return
    
    config = load_config(str(config_path))
    print(f"Da nap cau hinh tu {config_path}")
    
    # 1. Nạp và validate mô hình
    print("\n=== Bước 1: Nạp mô hình ===")
    inp_path = config['inp_path']
    if not os.path.isabs(inp_path):
        inp_path = str(project_root / inp_path)
    
    model_loader = ModelLoader(inp_path)
    success, message = model_loader.load_and_validate()
    
    if not success:
        print(f"Loi: {message}")
        return
    
    print(f"OK: {message}")
    
    # 2. Lấy danh sách nodes có thể có rò rỉ
    print("\n=== Bước 2: Xác định nodes rò rỉ ===")
    leak_node_list = config['leak_nodes'].get('node_list')
    
    if not leak_node_list:
        # Dung tat ca junctions
        leak_node_list = model_loader.get_junction_nodes()
        print(f"OK: Su dung tat ca {len(leak_node_list)} junction nodes")
    else:
        # Validate nodes
        all_nodes = model_loader.get_all_nodes()
        valid_nodes = [n for n in leak_node_list if n in all_nodes]
        if len(valid_nodes) != len(leak_node_list):
            invalid_nodes = set(leak_node_list) - set(valid_nodes)
            print(f"Canh bao: Co {len(invalid_nodes)} nodes khong ton tai: {invalid_nodes}")
        leak_node_list = valid_nodes
        print(f"OK: Su dung {len(leak_node_list)} nodes duoc chi dinh")
    
    if not leak_node_list:
        print("Loi: Khong co nodes hop le de tao ro ri")
        return
    
    # 3. Sinh kịch bản
    print("\n=== Bước 3: Sinh kịch bản rò rỉ ===")
    
    # Get leaks_per_scenario from config (default: 1)
    leaks_per_scenario = config['leak_nodes'].get('leaks_per_scenario', 1)
    print(f"OK: Leaks per scenario: {leaks_per_scenario}")
    
    scenario_generator = LeakScenarioGenerator(
        leak_nodes=leak_node_list,
        leak_area_range=config['leak_area_m2'],
        leak_time_range=config['leak_time_h'],
        discharge_coeff=config['discharge_coeff'],
        leaks_per_scenario=leaks_per_scenario
    )
    
    # Check if we should ensure all nodes are covered
    ensure_all_nodes = config.get('ensure_all_nodes_covered', False)
    if ensure_all_nodes:
        print(f"OK: Dam bao TAT CA {len(leak_node_list)} nodes deu co leak scenarios")
    else:
        print(f"Luu y: Chua bat ensure_all_nodes_covered - mot so nodes co the khong co leaks")
    
    scenarios = scenario_generator.generate(
        n_scenarios=config['n_scenarios'],
        simulation_duration_h=config['simulation']['duration_h'],
        ensure_all_nodes=ensure_all_nodes  # FIX: Pass parameter tu config
    )
    print(f"OK: Da sinh {len(scenarios)} kich ban")
    
    # 4. Chạy mô phỏng
    print("\n=== Bước 4: Chạy mô phỏng ===")
    
    sim_config = config['simulation']
    noise_config = config['noise']
    export_config = config['export']  # Cần định nghĩa trước khi dùng trong worker_args
    parallel_config = config.get('parallel', {})
    
    # Khởi tạo noise injector (cho sequential mode, parallel mode sẽ dùng trong worker)
    noise_injector = NoiseInjector(
        pressure_sigma=noise_config['pressure_sigma'],
        flow_sigma=noise_config['flow_sigma'],
        enabled=noise_config.get('enabled', True)
    )
    
    # Chuẩn bị dữ liệu cho parallel processing
    if parallel_config.get('enabled', True):
        max_workers = parallel_config.get('max_workers')
        if max_workers is None:
            max_workers = mp.cpu_count()
        
        print(f"Su dung {max_workers} workers song song")
        
        # Chuẩn bị arguments (thêm output_dir, export_config và noise_config để worker lưu file trực tiếp)
        worker_args = [
            (
                scenario.to_dict(),
                inp_path,
                sim_config,
                config['out_dir'],
                export_config,
                noise_config
            )
            for scenario in scenarios
        ]
        
        # Chạy song song
        with mp.Pool(processes=max_workers) as pool:
            results = pool.map(run_scenario_worker, worker_args)
    else:
        # Chay tuan tu
        print("Chay tuan tu (khong song song)")
        simulator = LeakSimulator(
            model_loader=model_loader,
            duration_h=sim_config['duration_h'],
            hydraulic_timestep_h=sim_config['hydraulic_timestep_h'],
            report_timestep_h=sim_config['report_timestep_h']
        )
        
        results = []
        for scenario in scenarios:
            result = simulator.run_scenario(scenario)
            results.append(result)
    
    # Thong ke ket qua
    successful = sum(1 for r in results if r.get('success', False))
    failed = len(results) - successful
    print(f"OK: Hoan thanh: {successful} thanh cong, {failed} that bai")
    
    # 5. Thu thập metadata và xuất labels (files đã được lưu trong worker)
    print("\n=== Bước 5: Thu thập metadata và xuất labels ===")
    
    exporter = DataExporter(
        output_dir=config['out_dir'],
        timeseries_format=export_config['timeseries_format'],
        parquet_compression=export_config.get('parquet_compression', 'snappy')
    )
    
    # Danh sách metadata và labels
    all_metadata = []
    all_labels = []
    
    # Worker đã lưu file trực tiếp, giờ chỉ cần thu thập metadata
    for result in results:
        if not result.get('success', False):
            continue
        
        scenario_id = result['scenario_id']
        scenario_metadata = result.get('metadata', {})
        
        if scenario_metadata:
            all_metadata.append(scenario_metadata)
            
            # Chuẩn bị labels
            label = {
                'scenario_id': scenario_id,
                'has_leak': True,
                'leak_node': scenario_metadata.get('leak_node'),
                'leak_area_m2': scenario_metadata.get('leak_area_m2'),
                'leak_start_time_s': scenario_metadata.get('start_time_s'),
                'leak_duration_s': scenario_metadata.get('duration_s'),
                'leak_end_time_s': scenario_metadata.get('end_time_s'),
                'leak_start_time_h': scenario_metadata.get('start_time_h', scenario_metadata.get('start_time_s', 0) / 3600.0),
                'leak_duration_h': scenario_metadata.get('duration_h', scenario_metadata.get('duration_s', 0) / 3600.0),
                'leak_end_time_h': scenario_metadata.get('end_time_h', scenario_metadata.get('end_time_s', 0) / 3600.0),
                'discharge_coeff': scenario_metadata.get('discharge_coeff')
            }
            all_labels.append(label)
    
    # Xuất metadata và labels
    if export_config.get('save_metadata', True):
        exporter.export_metadata(all_metadata)
    
    if export_config.get('save_labels', True):
        exporter.export_labels(all_metadata)  # Dung metadata de tao labels
    
    print(f"\nOK: Hoan thanh! Du lieu da duoc luu vao: {config['out_dir']}")
    print(f"  - {successful} kich ban thanh cong")
    print(f"  - Metadata: {config['out_dir']}/metadata.csv")
    print(f"  - Labels: {config['out_dir']}/labels.csv")
    print(f"  - Time-series data: {config['out_dir']}/scenario_*/")


if __name__ == "__main__":
    main()

