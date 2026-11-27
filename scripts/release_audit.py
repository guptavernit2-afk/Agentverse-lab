"""Online release checks against package advisories and a pinned Gitleaks distribution."""
from argparse import ArgumentParser
from hashlib import sha256
from io import BytesIO
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
from tempfile import TemporaryDirectory
from urllib.request import urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = "8.30.1"
ARTIFACTS = {
    "win32": ("windows_x64.zip", "d29144deff3a68aa93ced33dddf84b7fdc26070add4aa0f4513094c8332afc4e"),
    "linux": ("linux_x64.tar.gz", "551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb"),
}


def fetch_tool(folder: Path) -> Path:
    if sys.platform not in ARTIFACTS:
        raise ValueError("supply --gitleaks for this operating system")
    filename, expected = ARTIFACTS[sys.platform]
    url = f"https://github.com/gitleaks/gitleaks/releases/download/v{VERSION}/gitleaks_{VERSION}_{filename}"
    with urlopen(url, timeout=60) as response:
        raw = response.read()
    if sha256(raw).hexdigest() != expected:
        raise ValueError("Gitleaks archive failed SHA-256 verification")
    name = "gitleaks.exe" if os.name == "nt" else "gitleaks"
    if filename.endswith(".zip"):
        with zipfile.ZipFile(BytesIO(raw)) as archive:
            data = archive.read(name)
    else:
        with tarfile.open(fileobj=BytesIO(raw), mode="r:gz") as archive:
            data = archive.extractfile(name).read()
    tool = folder / name
    tool.write_bytes(data)
    tool.chmod(0o700)
    return tool


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--gitleaks", type=Path)
    args = parser.parse_args()
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    subprocess.run(["uv", "audit", "--locked"], cwd=ROOT / "backend", check=True)
    subprocess.run([npm, "audit", "--audit-level=high"], cwd=ROOT / "frontend", check=True)
    with TemporaryDirectory() as folder:
        tool = args.gitleaks.resolve() if args.gitleaks else fetch_tool(Path(folder))
        subprocess.run([str(tool), "git", "--redact", "--no-banner", "--log-opts=--all", "."], cwd=ROOT, check=True)
        patch = subprocess.check_output(["git", "diff", "--cached", "--no-ext-diff", "--no-color"], cwd=ROOT)
        subprocess.run([str(tool), "stdin", "--redact", "--no-banner"], input=patch, cwd=ROOT, check=True)
        subprocess.run([str(tool), "dir", "--redact", "--no-banner", "frontend/dist"], cwd=ROOT, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
