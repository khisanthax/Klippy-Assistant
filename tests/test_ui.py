import os
import subprocess
import sys


def test_desktop_starts_and_closes_cleanly():
    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
    result = subprocess.run([sys.executable, "-m", "klippy.app", "--smoke-test"],
                            env=env, capture_output=True, text=True, timeout=25)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Traceback" not in result.stderr
    assert "RuntimeWarning" not in result.stderr
