"""Run final-design regressions in separate processes to release Qt/worker state."""
from pathlib import Path
import json
import os
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "work/UI-FINAL-IMPLEMENT/verification"
SUITES = (
    "test_trip.py", "test_trip_scope.py", "test_trip_ledger.py", "test_trip_undo.py",
    "test_odometer.py", "test_channel_bridge.py", "test_channel_editor.py", "test_channels.py",
    "test_log_statistics.py", "test_mitigation.py", "test_telemetry.py",
    "test_telemetry_exit_flush.py", "test_request_model_trace.py", "test_anthropic_shape.py",
    "test_claude_inbound.py", "test_auto_updates.py", "test_i18n.py", "test_ui_final.py",
)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    environment = dict(os.environ, QT_QPA_PLATFORM="offscreen", PYTHONUTF8="1",
                       PYTHONPATH=os.pathsep.join(map(str, (ROOT, ROOT / "src", ROOT / "tests"))))
    for key in tuple(environment):
        if key.lower() in ("http_proxy", "https_proxy", "all_proxy"):
            environment.pop(key)
    requested = tuple(sys.argv[1:])
    prior = OUTPUT / "results.json"
    results = json.loads(prior.read_text(encoding="utf-8")) if requested and prior.exists() else []
    for name in requested or SUITES + ("test_router.StorageTests", "test_router.AdapterTests"):
        command = ([sys.executable, "-X", "utf8", "-m", "unittest", "discover", "-s", "tests", "-p", name, "-q"]
                   if name.endswith(".py") else [sys.executable, "-X", "utf8", "-m", "unittest", name, "-q"])
        started = time.monotonic()
        try:
            run = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True,
                                 encoding="utf-8", errors="replace", timeout=120)
            output = run.stdout + run.stderr; code = run.returncode
        except subprocess.TimeoutExpired as error:
            output = "TIMEOUT after 120 seconds\n" + str(error); code = 124
        (OUTPUT / (name + ".txt")).write_text(output, encoding="utf-8")
        count = re.search(r"Ran (\d+) tests?", output)
        result = dict(suite=name, tests=int(count.group(1)) if count else 0,
                      passed=code == 0, seconds=round(time.monotonic() - started, 2))
        results = [r for r in results if r["suite"] != name] + [result]
        print(json.dumps(result), flush=True)
        (OUTPUT / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(dict(total=sum(r["tests"] for r in results), passed=all(r["passed"] for r in results))), flush=True)
    return 0 if all(r["passed"] for r in results) else 1


if __name__ == "__main__": raise SystemExit(main())
