"""Tests for tools.audit_swim_messages CLI behavior."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.audit_swim_messages import _is_unroutable
from utils.swim_message_audit import audit_swim_payload

UNROUTABLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<itws_msg>
  <hello>world</hello>
</itws_msg>
"""

ROUTABLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<ds:tfmDataService xmlns:ds="urn:us:gov:dot:faa:atm:tfm:tfmdataservice"
  xmlns:fdm="urn:us:gov:dot:faa:atm:tfm:flightdata">
  <fltdOutput>
    <fdm:fltdMessage msgType="arrivalInformation"/>
  </fltdOutput>
</ds:tfmDataService>
"""


class TestAuditSwimMessagesCli(unittest.TestCase):
    def test_is_unroutable_true_for_non_swim_xml(self):
        audit = audit_swim_payload(UNROUTABLE_XML)
        self.assertIsNone(audit.parse_error)
        self.assertTrue(_is_unroutable(audit))

    def test_is_unroutable_false_for_routable_xml(self):
        audit = audit_swim_payload(ROUTABLE_XML)
        self.assertIsNone(audit.parse_error)
        self.assertFalse(_is_unroutable(audit))

    def test_fail_on_unroutable_flag_exits_non_zero(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            (base / "weather.xml").write_text(UNROUTABLE_XML, encoding="utf-8")
            cmd = [
                sys.executable,
                "tools/audit_swim_messages.py",
                str(base),
                "--fail-on-unroutable",
            ]
            proc = subprocess.run(
                cmd, cwd=Path(__file__).resolve().parents[1], check=False
            )
            self.assertEqual(proc.returncode, 1)

    def test_without_fail_on_unroutable_stays_zero(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            (base / "weather.xml").write_text(UNROUTABLE_XML, encoding="utf-8")
            cmd = [sys.executable, "tools/audit_swim_messages.py", str(base)]
            proc = subprocess.run(
                cmd, cwd=Path(__file__).resolve().parents[1], check=False
            )
            self.assertEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
