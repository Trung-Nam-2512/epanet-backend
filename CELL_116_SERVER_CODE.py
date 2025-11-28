# CELL 116 CODE - FOR SERVER (Linux)
# Copy-paste code này vào Cell 116 trong notebook

# Import post-processing functions (WORKS ON BOTH LINUX & WINDOWS)
import sys
import os

# Get current working directory
current_dir = os.getcwd()
print(f"[DEBUG] Current directory: {current_dir}")

# Ensure we're at project root (Cell 4 already handled this)
# Just add project root to sys.path
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
    print(f"[DEBUG] Added to sys.path: {current_dir}")

# Verify scripts/ directory exists
scripts_dir = os.path.join(current_dir, 'scripts')
if os.path.exists(scripts_dir):
    print(f"[DEBUG] ✅ Found scripts/ at: {scripts_dir}")
else:
    print(f"[ERROR] ❌ scripts/ not found at: {scripts_dir}")
    print(f"[DEBUG] Current dir contents: {os.listdir(current_dir)}")
    
# Try import
try:
    from scripts.post_processing import (
        filter_combined, 
        evaluate_filtered,
        print_evaluation_results
    )
    print("[DEBUG] ✅ Successfully imported post_processing functions!")
except ModuleNotFoundError as e:
    print(f"[ERROR] ❌ Import failed: {e}")
    print(f"[DEBUG] sys.path: {sys.path}")
    # Troubleshooting info
    print("\n[TROUBLESHOOTING]")
    print(f"  1. Verify scripts/post_processing.py exists:")
    print(f"     $ ls -la scripts/post_processing.py")
    print(f"  2. Check Python can find it:")
    print(f"     >>> import os")
    print(f"     >>> os.path.exists('scripts/post_processing.py')")















