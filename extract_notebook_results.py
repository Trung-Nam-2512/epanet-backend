import json
import sys
import io

# Fix encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Read notebook
with open('notebooks/train_leak_detection.ipynb', 'r', encoding='utf-8') as f:
    notebook = json.load(f)

# Find cells with outputs containing metrics
print("=" * 80)
print("EXTRACTING RESULTS FROM NOTEBOOK")
print("=" * 80)
print()

for i, cell in enumerate(notebook['cells']):
    if 'outputs' not in cell or len(cell['outputs']) == 0:
        continue
    
    source = ''.join(cell.get('source', []))
    
    # Check if this cell is about metrics
    if not any(kw in source.lower() for kw in ['threshold', 'recall', 'f2', 'top-', 'metric', 'accuracy', 'precision', 'test', 'val', 'train', 'confusion']):
        continue
    
    # Extract outputs
    for output in cell['outputs']:
        if output.get('output_type') == 'stream' and 'text' in output:
            text = ''.join(output['text'])
            if any(kw in text.lower() for kw in ['threshold', 'recall', 'f2', 'top-', 'accuracy', 'precision', 'test', 'val', 'train']):
                print(f"\nCell {i}:")
                print("-" * 80)
                try:
                    print(f"Source preview: {source[:150]}...")
                except:
                    print("Source preview: [encoding issue]")
                print(f"\nOutput:")
                print(text)
                print()

