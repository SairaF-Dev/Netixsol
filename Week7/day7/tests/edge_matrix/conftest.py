from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
for path in (ROOT / "day7/tests", ROOT / "day7", ROOT / "day7/vapi_integration",
             ROOT / "day3/src", ROOT / "day4/src", ROOT / "day2"):
    sys.path.insert(0, str(path))


def pytest_addoption(parser):
    parser.addoption("--edge-report", default=None, help="Write matrix observations to this directory")


def pytest_sessionfinish(session, exitstatus):
    target = session.config.getoption("--edge-report")
    if target:
        from .harness import write_report
        write_report(Path(target), exitstatus)
