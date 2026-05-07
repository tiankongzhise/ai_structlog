import subprocess

result = subprocess.run(
    [".venv/Scripts/python.exe", "-m", "pytest", "tests/", "-v", "--tb=short"],
    capture_output=True,
    text=True,
    cwd="c:/Users/3700x/Desktop/ai/ai_structlog",
)
print("STDOUT (last 5000 chars):")
print(result.stdout[-5000:])
print("\nReturn code:", result.returncode)
