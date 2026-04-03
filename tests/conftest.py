"""Shared test configuration and fixtures for sphinx-ford tests."""

import hashlib
import tarfile
import urllib.request
from pathlib import Path

import pytest

pytest_plugins = "sphinx.testing.fixtures"

collect_ignore = ["roots"]

# Example projects for FORD bridge testing
EXAMPLE_PROJECTS = {
    "toml-f": {
        "url": "https://github.com/toml-f/toml-f/releases/download/v0.5.0/toml-f-0.5.0.tar.xz",
        "sha256": "9a6c129836d093efd0cab5a2a013330020682a82e8f59a3882e9ae3249c8281f",
        "dirname": "toml-f-0.5.0",
        "ford_file": "docs.md",
    },
}

# Cache tarballs in the project directory to avoid re-downloading
_CACHE_DIR = Path(__file__).parent.parent / ".cache" / "example_projects"


def _download_and_verify(url: str, dest: Path, expected_sha256: str) -> None:
    """Download a file and verify its SHA256 checksum."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, dest)
    sha256 = hashlib.sha256(dest.read_bytes()).hexdigest()
    if sha256 != expected_sha256:
        dest.unlink()
        raise ValueError(f"SHA256 mismatch for {url}: expected {expected_sha256}, got {sha256}")


def _extract_tarball(tarball: Path, dest_dir: Path) -> Path:
    """Extract a .tar.xz tarball and return the extracted directory."""
    with tarfile.open(tarball, "r:xz") as tf:
        tf.extractall(dest_dir)
    return dest_dir


@pytest.fixture(scope="session")
def rootdir():
    return Path(__file__).parent.absolute() / "roots"


@pytest.fixture(scope="session")
def toml_f_project(tmp_path_factory):
    """Download and extract toml-f, return the project directory.

    Downloads the release tarball on first run and caches it locally in
    .cache/example_projects/ so subsequent test runs start instantly.
    """
    info = EXAMPLE_PROJECTS["toml-f"]
    tarball_name = info["url"].rsplit("/", 1)[-1]
    cached_tarball = _CACHE_DIR / tarball_name

    # Download if not cached
    if not cached_tarball.exists():
        try:
            _download_and_verify(info["url"], cached_tarball, info["sha256"])
        except Exception as e:
            pytest.skip(f"Could not download toml-f tarball: {e}")

    # Verify cached tarball checksum
    sha256 = hashlib.sha256(cached_tarball.read_bytes()).hexdigest()
    if sha256 != info["sha256"]:
        cached_tarball.unlink()
        pytest.skip("Cached tarball has wrong checksum, deleted it. Re-run tests.")

    # Extract to temp directory
    extract_dir = tmp_path_factory.mktemp("toml_f")
    _extract_tarball(cached_tarball, extract_dir)

    project_dir = extract_dir / info["dirname"]
    if not project_dir.exists():
        pytest.skip(f"Expected directory {info['dirname']} not found in tarball")

    return project_dir


@pytest.fixture(scope="session")
def toml_f_ford_file(toml_f_project):
    """Return the path to toml-f's FORD project file."""
    ford_file = toml_f_project / EXAMPLE_PROJECTS["toml-f"]["ford_file"]
    if not ford_file.exists():
        pytest.skip(f"FORD project file not found: {ford_file}")
    return ford_file
