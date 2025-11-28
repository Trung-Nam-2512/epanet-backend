"""
Script chuyển đổi dữ liệu từ dataset (Parquet) sang Excel
Hỗ trợ nhiều tùy chọn xuất để xử lý dataset lớn
"""
import pandas as pd
import numpy as np
from pathlib import Path
import sys
from datetime import datetime
import argparse

def export_scenario_to_excel(scenario_id, dataset_dir="dataset", output_dir="excel_export"):
    """
    Xuất một scenario cụ thể sang Excel
    
    Args:
        scenario_id: ID của scenario cần xuất
        dataset_dir: Thư mục chứa dataset
        output_dir: Thư mục output
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    dataset_path = Path(dataset_dir)
    scenario_dir = dataset_path / f"scenario_{scenario_id:05d}"
    nodes_file = scenario_dir / "nodes.parquet"
    
    if not nodes_file.exists():
        print(f"[ERROR] Không tìm thấy file: {nodes_file}")
        return None
    
    print(f"[INFO] Đang đọc scenario {scenario_id}...")
    df = pd.read_parquet(nodes_file)
    print(f"[OK] Đã đọc {len(df):,} records")
    
    # Xuất ra Excel
    output_file = output_path / f"scenario_{scenario_id:05d}.xlsx"
    print(f"[INFO] Đang xuất ra Excel: {output_file}...")
    
    # Chia thành sheets nếu cần (Excel limit ~1M rows per sheet)
    max_rows_per_sheet = 1000000
    
    if len(df) <= max_rows_per_sheet:
        # Xuất trực tiếp vào 1 sheet
        df.to_excel(output_file, index=False, engine='openpyxl')
        print(f"[OK] Đã xuất {len(df):,} records vào {output_file}")
    else:
        # Chia thành nhiều sheets
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            n_sheets = (len(df) // max_rows_per_sheet) + 1
            for i in range(n_sheets):
                start_idx = i * max_rows_per_sheet
                end_idx = min((i + 1) * max_rows_per_sheet, len(df))
                df_sheet = df.iloc[start_idx:end_idx]
                sheet_name = f"Data_{i+1}" if n_sheets > 1 else "Data"
                df_sheet.to_excel(writer, sheet_name=sheet_name, index=False)
            print(f"[OK] Đã xuất {len(df):,} records vào {n_sheets} sheets trong {output_file}")
    
    return output_file

def export_scenarios_summary(dataset_dir="dataset", output_dir="excel_export", max_scenarios=None):
    """
    Xuất summary/statistics của nhiều scenarios
    
    Args:
        dataset_dir: Thư mục chứa dataset
        output_dir: Thư mục output
        max_scenarios: Số lượng scenarios tối đa (None = tất cả)
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    dataset_path = Path(dataset_dir)
    
    # Tìm tất cả scenarios
    scenario_dirs = sorted([d for d in dataset_path.glob("scenario_*") if d.is_dir()])
    
    if max_scenarios:
        scenario_dirs = scenario_dirs[:max_scenarios]
    
    print(f"[INFO] Đang xử lý {len(scenario_dirs)} scenarios...")
    
    summaries = []
    
    for i, scenario_dir in enumerate(scenario_dirs):
        scenario_id = int(scenario_dir.name.split('_')[1])
        nodes_file = scenario_dir / "nodes.parquet"
        
        if not nodes_file.exists():
            continue
        
        try:
            # Đọc một sample nhỏ để tính statistics
            df = pd.read_parquet(nodes_file)
            
            summary = {
                'scenario_id': scenario_id,
                'total_records': len(df),
                'num_nodes': df['node_id'].nunique(),
                'num_timesteps': df['timestamp'].nunique(),
                'duration_hours': df['timestamp'].max() / 3600,
                'pressure_mean': df['pressure'].mean(),
                'pressure_std': df['pressure'].std(),
                'pressure_min': df['pressure'].min(),
                'pressure_max': df['pressure'].max(),
                'demand_mean': df['demand'].mean(),
                'demand_std': df['demand'].std(),
                'demand_max': df['demand'].max(),
                'has_leak_demand': (df['leak_demand'] > 0).any(),
                'leak_demand_max': df['leak_demand'].max() if df['leak_demand'].max() > 0 else 0,
                'leak_records': (df['leak_demand'] > 0).sum()
            }
            summaries.append(summary)
            
            if (i + 1) % 100 == 0:
                print(f"  Đã xử lý {i + 1}/{len(scenario_dirs)} scenarios...")
        except Exception as e:
            print(f"  [WARNING] Lỗi khi xử lý scenario {scenario_id}: {e}")
            continue
    
    # Tạo DataFrame và xuất
    df_summary = pd.DataFrame(summaries)
    output_file = output_path / "scenarios_summary.xlsx"
    
    print(f"[INFO] Đang xuất summary ra Excel...")
    df_summary.to_excel(output_file, index=False, engine='openpyxl')
    print(f"[OK] Đã xuất summary của {len(summaries)} scenarios vào {output_file}")
    
    return output_file

def export_scenario_samples(dataset_dir="dataset", output_dir="excel_export", 
                           scenario_ids=None, samples_per_scenario=1000):
    """
    Xuất samples từ các scenarios (để xem dữ liệu mẫu)
    
    Args:
        dataset_dir: Thư mục chứa dataset
        output_dir: Thư mục output
        scenario_ids: List scenario IDs (None = lấy 5 đầu tiên)
        samples_per_scenario: Số records mẫu mỗi scenario
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    dataset_path = Path(dataset_dir)
    
    if scenario_ids is None:
        # Lấy 5 scenarios đầu tiên
        all_dirs = sorted([d for d in dataset_path.glob("scenario_*") if d.is_dir()])
        scenario_ids = [int(d.name.split('_')[1]) for d in all_dirs[:5]]
    
    print(f"[INFO] Đang xuất samples từ {len(scenario_ids)} scenarios...")
    
    all_samples = []
    
    for scenario_id in scenario_ids:
        scenario_dir = dataset_path / f"scenario_{scenario_id:05d}"
        nodes_file = scenario_dir / "nodes.parquet"
        
        if not nodes_file.exists():
            print(f"[WARNING] Không tìm thấy scenario {scenario_id}")
            continue
        
        df = pd.read_parquet(nodes_file)
        
        # Sample ngẫu nhiên hoặc đầu tiên
        if len(df) > samples_per_scenario:
            # Lấy đầu tiên, giữa, và cuối
            n = samples_per_scenario // 3
            sample_df = pd.concat([
                df.head(n),
                df.iloc[len(df)//2:len(df)//2+n],
                df.tail(n)
            ]).drop_duplicates()
        else:
            sample_df = df
        
        all_samples.append(sample_df)
        print(f"  [OK] Scenario {scenario_id}: {len(sample_df):,} samples")
    
    # Combine và xuất
    df_samples = pd.concat(all_samples, ignore_index=True)
    output_file = output_path / "scenarios_samples.xlsx"
    
    print(f"[INFO] Đang xuất samples ra Excel...")
    df_samples.to_excel(output_file, index=False, engine='openpyxl')
    print(f"[OK] Đã xuất {len(df_samples):,} sample records vào {output_file}")
    
    return output_file

def export_with_metadata(dataset_dir="dataset", output_dir="excel_export", scenario_ids=None):
    """
    Xuất scenarios kèm metadata (từ metadata.csv)
    
    Args:
        dataset_dir: Thư mục chứa dataset
        output_dir: Thư mục output
        scenario_ids: List scenario IDs (None = tất cả)
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    dataset_path = Path(dataset_dir)
    metadata_file = dataset_path / "metadata.csv"
    
    if not metadata_file.exists():
        print(f"[ERROR] Không tìm thấy metadata.csv")
        return None
    
    # Đọc metadata
    metadata_df = pd.read_csv(metadata_file)
    
    if scenario_ids:
        metadata_df = metadata_df[metadata_df['scenario_id'].isin(scenario_ids)]
    
    print(f"[INFO] Đang xuất {len(metadata_df)} scenarios với metadata...")
    
    output_file = output_path / f"scenarios_with_metadata_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Sheet 1: Metadata
        metadata_df.to_excel(writer, sheet_name='Metadata', index=False)
        
        # Sheet 2: Sample data từ scenarios đầu tiên (nếu không quá nhiều)
        if len(metadata_df) <= 10:
            for idx, row in metadata_df.head(10).iterrows():
                scenario_id = row['scenario_id']
                scenario_dir = dataset_path / f"scenario_{scenario_id:05d}"
                nodes_file = scenario_dir / "nodes.parquet"
                
                if nodes_file.exists():
                    df = pd.read_parquet(nodes_file)
                    # Giới hạn 10000 rows per scenario để không quá lớn
                    if len(df) > 10000:
                        df = df.sample(n=10000, random_state=42).sort_values(['timestamp', 'node_id'])
                    
                    sheet_name = f"Scenario_{scenario_id}"
                    if len(sheet_name) > 31:  # Excel sheet name limit
                        sheet_name = f"S_{scenario_id}"
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    print(f"[OK] Đã xuất vào {output_file}")
    return output_file

def main():
    parser = argparse.ArgumentParser(
        description="Chuyển đổi dataset Parquet sang Excel",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ sử dụng:
  # Xuất 1 scenario cụ thể
  python scripts/export_to_excel.py --scenario 1
  
  # Xuất summary của tất cả scenarios
  python scripts/export_to_excel.py --summary
  
  # Xuất samples từ 5 scenarios đầu tiên
  python scripts/export_to_excel.py --samples
  
  # Xuất nhiều scenarios cụ thể
  python scripts/export_to_excel.py --scenarios 1 2 3 4 5
  
  # Xuất với metadata
  python scripts/export_to_excel.py --with-metadata
        """
    )
    
    parser.add_argument('--scenario', type=int, help='Xuất một scenario cụ thể')
    parser.add_argument('--scenarios', type=int, nargs='+', help='Xuất nhiều scenarios cụ thể')
    parser.add_argument('--summary', action='store_true', help='Xuất summary của tất cả scenarios')
    parser.add_argument('--samples', action='store_true', help='Xuất samples từ một vài scenarios')
    parser.add_argument('--with-metadata', action='store_true', help='Xuất scenarios kèm metadata')
    parser.add_argument('--dataset-dir', default='dataset', help='Thư mục dataset (default: dataset)')
    parser.add_argument('--output-dir', default='excel_export', help='Thư mục output (default: excel_export)')
    parser.add_argument('--max-scenarios', type=int, help='Giới hạn số scenarios (cho summary)')
    
    args = parser.parse_args()
    
    # Nếu không có arguments, hiển thị help
    if len(sys.argv) == 1:
        parser.print_help()
        return
    
    print("="*80)
    print("CHUYEN DOI DATASET SANG EXCEL")
    print("="*80)
    print()
    
    try:
        if args.scenario:
            # Xuất 1 scenario
            export_scenario_to_excel(args.scenario, args.dataset_dir, args.output_dir)
        
        elif args.scenarios:
            # Xuất nhiều scenarios
            for sid in args.scenarios:
                export_scenario_to_excel(sid, args.dataset_dir, args.output_dir)
        
        elif args.summary:
            # Xuất summary
            export_scenarios_summary(args.dataset_dir, args.output_dir, args.max_scenarios)
        
        elif args.samples:
            # Xuất samples
            export_scenario_samples(args.dataset_dir, args.output_dir)
        
        elif args.with_metadata:
            # Xuất với metadata
            export_with_metadata(args.dataset_dir, args.output_dir)
        
        else:
            print("[INFO] Không có tùy chọn nào được chọn. Sử dụng --help để xem hướng dẫn.")
            print()
            print("Tùy chọn nhanh:")
            print("  --summary        : Xuất summary của tất cả scenarios")
            print("  --samples         : Xuất samples từ 5 scenarios đầu tiên")
            print("  --scenario N      : Xuất scenario N")
    
    except Exception as e:
        print(f"[ERROR] Lỗi: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

