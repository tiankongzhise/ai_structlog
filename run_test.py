import sys

sys.path.insert(0, "src")
sys.path.insert(0, "tests")

try:
    print("Import OK")
except Exception as e:
    print(f"Error: {e}")
    import traceback

    traceback.print_exc()
