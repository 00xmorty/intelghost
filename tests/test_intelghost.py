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


class CoverageTests(unittest.TestCase):
    def test_bundled_helpers_are_opt_in(self):
        with TemporaryDirectory() as td:
            root = Path(td) / "Fixture.app"
            helpers = [root / "Contents/Resources/helper-intel",
                       root / "Contents/Resources/node_modules/package/nested-intel",
                       root / "Contents/MacOS/node_modules/package/other-intel"]
            for helper in helpers:
                helper.parent.mkdir(parents=True, exist_ok=True)
                macho_file(helper)
            mod = load_module()
            self.assertEqual(list(mod.iter_files([root], 100)), [])
            self.assertEqual(set(mod.iter_files([root], 100, True)), set(helpers))
            self.assertEqual(list(mod.iter_files([helpers[0]], 100)), [helpers[0]])

    def test_expanded_scan_retains_exclusions_and_no_directory_symlink_following(self):
        with TemporaryDirectory() as td:
            root = Path(td) / "app"
            outside = Path(td) / "outside"
            outside.mkdir()
            macho_file(outside / "outside-intel")
            root.mkdir()
            (root / "linked").symlink_to(outside, target_is_directory=True)
            for directory in (".git", "Caches", "DerivedData", "__pycache__"):
                (root / directory).mkdir()
                macho_file(root / directory / "hidden-intel")
            self.assertEqual(list(load_module().iter_files([root], 100, True)), [])

    def test_global_cap_includes_explicit_file_roots(self):
        with TemporaryDirectory() as td:
            paths = [Path(td) / name for name in ("first", "second", "third")]
            for path in paths:
                macho_file(path)
            coverage = {}
            found = list(load_module().iter_files(paths, 2, True, coverage))
            self.assertEqual(found, paths[:2])
            self.assertEqual(coverage, {"visited_files": 2, "file_limit_reached": True})

    def test_exact_cap_does_not_claim_truncation(self):
        with TemporaryDirectory() as td:
            path = Path(td) / "one"
            macho_file(path)
            coverage = {}
            self.assertEqual(list(load_module().iter_files([path], 1, True, coverage)), [path])
            self.assertFalse(coverage["file_limit_reached"])

    def test_json_expanded_scan_and_partial_warning(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            make_fake_lipo(root)
            app = root / "Fixture.app"
            folder = app / "Contents/Resources/node_modules/example"
            folder.mkdir(parents=True)
            for name in ("a-intel", "b-intel"):
                macho_file(folder / name)
            env = dict(os.environ, PATH=str(root) + os.pathsep + os.environ.get("PATH", ""))
            base = [sys.executable, str(CLI), "--path", str(app), "--include-bundled", "--max-files", "1"]
            result = subprocess.run(base + ["--json"], capture_output=True, text=True, env=env)
            self.assertEqual(result.returncode, 2, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data["intel_only_count"], 1)
            self.assertEqual(data["affected_component_count"], 1)
            self.assertTrue(data["coverage"]["include_bundled"])
            self.assertTrue(data["coverage"]["file_limit_reached"])
            self.assertEqual(data["coverage"]["visited_files"], 1)
            self.assertNotIn("node_modules", data["coverage"]["excluded_directories"])
            self.assertFalse(data["coverage"]["excludes_contents_resources"])
            text = subprocess.run(base + ["--quiet"], capture_output=True, text=True, env=env)
            self.assertIn("results are partial", text.stdout)
            default = subprocess.run([sys.executable, str(CLI), "--path", str(app), "--quiet"], capture_output=True, text=True, env=env)
            self.assertIn("--include-bundled", default.stdout)
            self.assertEqual(default.returncode, 0)


if __name__ == "__main__":
    unittest.main()
