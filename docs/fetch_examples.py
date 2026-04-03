"""Fetch example project sources for documentation builds.

Downloads and extracts release tarballs for the example projects used
in the sphinx-ford documentation.  Cached in docs/_examples_src/.
"""

import hashlib
import tarfile
import urllib.request
from pathlib import Path

EXAMPLES = {
    "toml-f": {
        "url": "https://github.com/toml-f/toml-f/releases/download/v0.5.0/toml-f-0.5.0.tar.xz",
        "sha256": "9a6c129836d093efd0cab5a2a013330020682a82e8f59a3882e9ae3249c8281f",
        "dirname": "toml-f-0.5.0",
        "ford_file": "docs.md",
    },
    "fpm": {
        "url": "https://github.com/fortran-lang/fpm/archive/refs/tags/v0.13.0.tar.gz",
        "sha256": "6cb305bbc9a2f351b8dc8908d96ca198ba732f93707c6bb38d99e79647a72564",
        "dirname": "fpm-0.13.0",
        "ford_file": "docs.md",
    },
    "aotus": {
        "url": "https://github.com/apes-suite/aotus/archive/refs/tags/v1.0.4.tar.gz",
        "sha256": "eba51e67c00eac2a124b54b8b1460244edf8bce2a1028986e16f4e5589f24ea7",
        "dirname": "aotus-1.0.4",
        "ford_file": "aot_mainpage.md",
    },
    "stdlib": {
        "url": "https://github.com/fortran-lang/stdlib/archive/refs/tags/v0.8.1.tar.gz",
        "sha256": "6d20b120a4b17fb23ee5353408f6826b521bd006cd42eb412b01984eb9c31ded",
        "dirname": "stdlib-0.8.1",
        "ford_file": "API-doc-FORD-file.md",
        "preprocess": False,  # fypp not available in docs build
    },
    "dbcsr": {
        "url": "https://github.com/cp2k/dbcsr/archive/refs/tags/v2.9.1.tar.gz",
        "sha256": "5cc9e9f41cf58697374baf7a45326e26860a755aecf22a7c9333152ec09fe7bd",
        "dirname": "dbcsr-2.9.1",
        "ford_file": "DBCSR.md",
        "vars": {},  # populated at build time with CMAKE_SOURCE_DIR etc
    },
}

CACHE_DIR = Path(__file__).parent / "_examples_src"


def fetch(name: str) -> Path:
    """Fetch and extract an example project, return its directory."""
    info = EXAMPLES[name]
    tarball_name = info["url"].rsplit("/", 1)[-1]
    cached_tarball = CACHE_DIR / tarball_name
    project_dir = CACHE_DIR / info["dirname"]

    if project_dir.exists():
        return project_dir

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if not cached_tarball.exists():
        print(f"Downloading {info['url']}...")
        urllib.request.urlretrieve(info["url"], cached_tarball)

    sha256 = hashlib.sha256(cached_tarball.read_bytes()).hexdigest()
    if sha256 != info["sha256"]:
        cached_tarball.unlink()
        raise RuntimeError(f"SHA256 mismatch for {tarball_name}")

    print(f"Extracting {tarball_name}...")
    if tarball_name.endswith(".tar.xz"):
        mode = "r:xz"
    elif tarball_name.endswith(".tar.gz"):
        mode = "r:gz"
    else:
        mode = "r"
    with tarfile.open(cached_tarball, mode) as tf:
        tf.extractall(CACHE_DIR)

    return project_dir


def fetch_all():
    """Fetch all example projects."""
    for name in EXAMPLES:
        path = fetch(name)
        print(f"  {name}: {path}")


if __name__ == "__main__":
    fetch_all()
