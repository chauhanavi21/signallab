"""Run all core/HTTP tests and regenerate evidence; no optional packages needed."""
import json
import os
import platform
import unittest
from datetime import datetime, timezone
from pathlib import Path
from evidence import generate
from real_data_check import main as check_real_data


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    os.chdir(root)
    result = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.discover("tests"))
    record = {"checked_at":datetime.now(timezone.utc).isoformat(), "python":platform.python_version(),
              "command":"python verify.py", "tests_run":result.testsRun, "failures":len(result.failures),
              "errors":len(result.errors), "skipped":len(result.skipped), "successful":result.wasSuccessful()}
    if result.wasSuccessful():
        record["evidence"]=generate()
        check_real_data()
        record["real_data_passed"]=True
    (root / "artifacts").mkdir(exist_ok=True)
    (root / "artifacts/verification.json").write_text(json.dumps(record,indent=2),encoding="utf-8")
    print(json.dumps({key:value for key,value in record.items() if key!="evidence"},indent=2))
    raise SystemExit(0 if result.wasSuccessful() else 1)
