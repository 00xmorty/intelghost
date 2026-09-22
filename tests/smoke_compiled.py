"""macOS integration: compile real Intel/ARM objects; never execute them."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

CLI = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "intelghost"


def main():
    if sys.platform != "darwin":
        raise SystemExit("This integration smoke requires macOS clang and lipo.")
    with TemporaryDirectory(prefix="intelghost-smoke-", dir=os.environ.get("TMPDIR")) as td:
        root = Path(td)
        app = root / "CoverageFixture.app"
        folder = app / "Contents/Resources/node_modules/example"
        folder.mkdir(parents=True)
        source = root / "helper.c"
        source.write_text("int fixture(void) { return 0; }\n")
        for arch in ("x86_64", "arm64"):
            subprocess.run(["xcrun", "clang", "-target", f"{arch}-apple-macos11", "-c", str(source), "-o", str(folder / (arch + ".o"))], check=True)
        helper = folder / "x86_64.o"
        assert subprocess.check_output(["lipo", "-archs", str(helper)], text=True).strip() == "x86_64"
        before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir()}
        cases = [("default_app", app, [], 0, 0),
                 ("expanded_app", app, ["--include-bundled"], 1, 2),
                 ("exact_helper", helper, [], 1, 2)]
        summary = {}
        for label, path, flags, expected, code in cases:
            result = subprocess.run([sys.executable, str(CLI), "--path", str(path), "--json", *flags], text=True, capture_output=True)
            assert result.returncode == code, result.stderr
            data = json.loads(result.stdout)
            assert data["intel_only_count"] == expected, data
            assert data["affected_component_count"] == expected, data
            assert not data["coverage"]["file_limit_reached"], data
            summary[label] = {"intel_only_count": expected, "exit_code": code,
                              "scanned_macho_files": data["scanned_macho_files"]}
        assert summary["expanded_app"]["scanned_macho_files"] == 2
        after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir()}
        assert before == after, "Scan modified fixture bytes"
        summary["fixture_bytes_unchanged"] = True
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
