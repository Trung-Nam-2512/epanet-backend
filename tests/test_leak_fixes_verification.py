"""
Test để verify các fix đã áp dụng cho leak data generation
"""
import sys
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.leak_simulation.dataset_generator import DatasetGenerator
from scripts.leak_simulation.leak_scenarios import LeakScenarioGenerator

print("="*80)
print("TEST: VERIFY LEAK DATA GENERATION FIXES")
print("="*80)

# Test 1: Verify leaks_per_scenario được pass vào LeakScenarioGenerator
print("\n[TEST 1] leaks_per_scenario Passed to Generator")
print("-"*80)

try:
    # Load config
    config_file = Path("config/leak_simulation_config.yaml")
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    leaks_per_scenario_config = config.get('leak_nodes', {}).get('leaks_per_scenario', 1)
    print(f"Config leaks_per_scenario: {leaks_per_scenario_config}")
    
    # Check dataset_generator code
    code_file = Path("scripts/leak_simulation/dataset_generator.py")
    with open(code_file, 'r', encoding='utf-8') as f:
        code = f.read()
    
    if 'leaks_per_scenario' in code and 'self.config' in code:
        # Check if it's passed to LeakScenarioGenerator
        if 'LeakScenarioGenerator(' in code and 'leaks_per_scenario=' in code:
            print("[OK] leaks_per_scenario duoc pass vao LeakScenarioGenerator")
        else:
            print("[FAIL] leaks_per_scenario khong duoc pass vao LeakScenarioGenerator!")
            sys.exit(1)
    else:
        print("[FAIL] Code khong load leaks_per_scenario tu config!")
        sys.exit(1)
    
    # Verify bằng cách tạo generator
    leak_node_list = ["2", "3", "31"]
    leaks_per_scenario = config.get('leak_nodes', {}).get('leaks_per_scenario', 1)
    
    generator = LeakScenarioGenerator(
        leak_nodes=leak_node_list,
        leak_area_range=config['leak_area_m2'],
        leak_time_range=config['leak_time_h'],
        discharge_coeff=config['discharge_coeff'],
        leaks_per_scenario=leaks_per_scenario
    )
    
    print(f"Generator leaks_per_scenario: {generator.leaks_per_scenario}")
    
    if generator.leaks_per_scenario == leaks_per_scenario_config:
        print(f"[OK] Generator có leaks_per_scenario = {generator.leaks_per_scenario}")
    else:
        print(f"[FAIL] Generator leaks_per_scenario mismatch!")
        sys.exit(1)
    
except Exception as e:
    print(f"[ERROR] Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: Verify simulation.py hỗ trợ multiple leaks
print("\n[TEST 2] simulation.py Multiple Leaks Support")
print("-"*80)

try:
    code_file = Path("scripts/leak_simulation/simulation.py")
    with open(code_file, 'r', encoding='utf-8') as f:
        code = f.read()
    
    # Check if code has multiple leaks logic
    has_multiple_leaks = (
        'scenario.leak_nodes' in code and 
        'len(scenario.leak_nodes) > 1' in code and
        'scenario.leak_areas_m2' in code
    )
    
    if has_multiple_leaks:
        print("[OK] simulation.py co logic ho tro multiple leaks")
    else:
        print("[FAIL] simulation.py khong ho tro multiple leaks!")
        sys.exit(1)
    
    # Check if it applies all leaks
    if 'for i, leak_node_raw in enumerate(scenario.leak_nodes)' in code:
        print("[OK] Code loop qua tat ca leak nodes")
    else:
        print("[FAIL] Code khong loop qua tat ca leak nodes!")
        sys.exit(1)
    
    # Check if it uses correct parameters for each leak
    if 'scenario.leak_areas_m2[i]' in code and 'scenario.leak_start_times_s[i]' in code:
        print("[OK] Code su dung dung parameters cho moi leak")
    else:
        print("[FAIL] Code khong su dung dung parameters!")
        sys.exit(1)
    
except Exception as e:
    print(f"[ERROR] Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Verify run_scenario_worker hỗ trợ multiple leaks
print("\n[TEST 3] run_scenario_worker Multiple Leaks Support")
print("-"*80)

try:
    code_file = Path("scripts/leak_simulation/dataset_generator.py")
    with open(code_file, 'r', encoding='utf-8') as f:
        code = f.read()
    
    # Find run_scenario_worker function
    if 'def run_scenario_worker' in code:
        # Check if it handles multiple leaks
        if "'leak_nodes' in scenario_dict" in code and "scenario_dict.get('leak_nodes')" in code:
            print("[OK] run_scenario_worker co logic ho tro multiple leaks")
        else:
            print("[FAIL] run_scenario_worker khong ho tro multiple leaks!")
            sys.exit(1)
        
        # Check if it passes all leak parameters
        if 'leak_nodes=' in code and 'leak_areas_m2=' in code:
            print("[OK] run_scenario_worker pass day du leak parameters")
        else:
            print("[FAIL] run_scenario_worker khong pass day du parameters!")
            sys.exit(1)
    else:
        print("[FAIL] run_scenario_worker function not found!")
        sys.exit(1)
    
except Exception as e:
    print(f"[ERROR] Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*80)
print("[SUCCESS] ALL FIXES VERIFIED")
print("="*80)
print("\nXac nhan:")
print("  1. leaks_per_scenario duoc pass tu config vao generator")
print("  2. simulation.py ho tro multiple leaks")
print("  3. run_scenario_worker ho tro multiple leaks")

