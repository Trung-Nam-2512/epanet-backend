"""Script để đọc output từ Jupyter notebook"""
import json
from pathlib import Path

def read_notebook_outputs(notebook_path):
    """Đọc tất cả outputs từ notebook"""
    with open(notebook_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    results = {}
    
    for i, cell in enumerate(data['cells']):
        if 'outputs' not in cell or len(cell['outputs']) == 0:
            continue
        
        # Tìm source code để hiểu cell này làm gì
        source = ''.join(cell.get('source', []))
        
        # Tìm các outputs có text
        for output in cell['outputs']:
            if output.get('output_type') == 'stream' and 'text' in output:
                text = ''.join(output['text'])
                if any(keyword in source.lower() for keyword in ['threshold', 'recall', 'f2', 'top-', 'metric', 'accuracy', 'precision', 'confusion']):
                    results[f'cell_{i}'] = {
                        'source': source[:200] + '...' if len(source) > 200 else source,
                        'output': text
                    }
            elif output.get('output_type') == 'execute_result' and 'data' in output:
                if 'text/plain' in output['data']:
                    text = ''.join(output['data']['text/plain'])
                    if any(keyword in source.lower() for keyword in ['threshold', 'recall', 'f2', 'top-', 'metric', 'accuracy', 'precision', 'confusion']):
                        results[f'cell_{i}'] = {
                            'source': source[:200] + '...' if len(source) > 200 else source,
                            'output': text
                        }
    
    return results

if __name__ == '__main__':
    notebook_path = Path('notebooks/train_leak_detection.ipynb')
    if not notebook_path.exists():
        print(f"Notebook not found: {notebook_path}")
        exit(1)
    
    print("=" * 80)
    print("DOC KET QUA TU NOTEBOOK")
    print("=" * 80)
    print()
    
    results = read_notebook_outputs(notebook_path)
    
    for cell_id, data in results.items():
        print(f"\n{cell_id}:")
        print("-" * 80)
        print(f"Source: {data['source'][:100]}...")
        print(f"Output:\n{data['output']}")
        print()

