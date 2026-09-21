import importlib.machinery
import importlib.util
import json
import os
import stat
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "intelghost"


def load_module():
    loader = importlib.machinery.SourceFileLoader("intelghost", str(CLI))
    spec = importlib.util.spec_from_loader("intelghost", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def make_fake_lipo(tmp_path: Path) -> None:
    fake = tmp_path / "lipo"
    fake.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "p=sys.argv[-1]\n"
        "print('x86_64' if 'intel' in p else 'x86_64 arm64')\n",
        encoding="utf-8",
    )
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR)


def macho_file(path: Path) -> None:
    path.write_bytes(b"\xcf\xfa\xed\xfe" + b"fixture")


class IntelGhostTests(unittest.TestCase):
    def test_classify_arches(self):
        mod = load_module()
        self.assertEqual(mod.classify(["x86_64"]), "intel_only")
        self.assertEqual(mod.classify(["x86_64", "arm64"]), "universal")
        self.assertEqual(mod.classify(["arm64e"]), "apple_silicon_only")

    def test_component_owner_for_nested_bundle(self):
        mod = load_module()
        path = Path("/Library/Audio/Plug-Ins/VST/Legacy.vst/Contents/MacOS/Legacy")
        self.assertEqual(
            mod.component_for(path),
            {
                "name": "Legacy.vst",
                "type": "vst",
                "path": "/Library/Audio/Plug-Ins/VST/Legacy.vst",
            },
        )

    def test_json_scan_with_fake_lipo(self):
        with TemporaryDirectory() as td:
            tmp_path = Path(td)
            make_fake_lipo(tmp_path)
            fixture_dir = tmp_path / "fixtures"
            fixture_dir.mkdir()
            legacy_dir = fixture_dir / "Legacy.vst" / "Contents" / "MacOS"
            legacy_dir.mkdir(parents=True)
            macho_file(legacy_dir / "legacy-intel")
            macho_file(legacy_dir / "legacy-intel-helper")
            macho_file(fixture_dir / "modern-universal.bundle")
            (fixture_dir / "plain.txt").write_text("not macho", encoding="utf-8")
            env = os.environ.copy()
            env["PATH"] = str(tmp_path) + os.pathsep + env.get("PATH", "")
            proc = subprocess.run(
                [sys.executable, str(CLI), "--json", "--path", str(fixture_dir)],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            self.assertEqual(proc.returncode, 2, proc.stderr + proc.stdout)
            data = json.loads(proc.stdout)
            self.assertEqual(data["intel_only_count"], 2)
            self.assertEqual(data["affected_component_count"], 1)
            self.assertEqual(data["findings"][0]["component"], "Legacy.vst")
            self.assertEqual(data["findings"][0]["component_type"], "vst")
            self.assertEqual(data["findings"][0]["archs"], ["x86_64"])

    def test_text_scan_no_findings(self):
        with TemporaryDirectory() as td:
            tmp_path = Path(td)
            make_fake_lipo(tmp_path)
            fixture_dir = tmp_path / "fixtures"
            fixture_dir.mkdir()
            macho_file(fixture_dir / "modern-universal.bundle")
            env = os.environ.copy()
            env["PATH"] = str(tmp_path) + os.pathsep + env.get("PATH", "")
            proc = subprocess.run(
                [sys.executable, str(CLI), "--path", str(fixture_dir)],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            self.assertIn("Intel-only findings: 0", proc.stdout)
            self.assertIn("Affected components: 0", proc.stdout)


if __name__ == "__main__":
    unittest.main()
