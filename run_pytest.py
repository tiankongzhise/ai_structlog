import subprocess
import sys

# 设置 UTF-8 编码
sys.stdout.reconfigure(encoding="utf-8")

# 工作目录
WORK_DIR = r"c:/Users/3700x/Desktop/ai/ai_structlog"

# 先清理旧的覆盖率数据
subprocess.run([sys.executable, "-m", "coverage", "erase"], cwd=WORK_DIR, capture_output=True)

# ==================== 关键修改：使用 pytest-cov 代替 coverage run ====================
with open("test_result.txt", "w", encoding="utf-8") as f:
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/",
            "-v",
            "--tb=short",
            "-n",
            "auto",  # 多进程
            "--cov=tkzs_structlog",  # <--- 改成你要统计覆盖率的包名
            "--cov-report=term-missing",  # 控制台输出（显示未覆盖行）
            "--cov-report=html",  # HTML报告
            "--cov-append",  # 多进程覆盖率合并
        ],
        cwd=WORK_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
    )

    # 流式输出
    for line in iter(process.stdout.readline, ""):
        sys.stdout.write(line)
        sys.stdout.flush()
        f.write(line)
        f.flush()

    process.stdout.close()
    return_code = process.wait()

# 因为用了 pytest-cov，自动合并多进程覆盖率，不需要手动 coverage combine / coverage report
print(f"\n[OK] Test finished! Exit code: {return_code}")
print("[INFO] Results saved to test_result.txt")
print("[INFO] Coverage report: htmlcov/index.html")
