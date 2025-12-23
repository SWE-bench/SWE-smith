from pathlib import Path

__version__ = "0.0.7"
PACKAGE_BASE_DIR = Path(__file__).resolve().parent
REPO_DIR = PACKAGE_BASE_DIR.parent


__all__ = ["PACKAGE_BASE_DIR", "REPO_DIR", "__version__"]
