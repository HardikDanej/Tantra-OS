"""
Tests for the repo's tools/ scripts. tools/ is a folder of standalone CLI
scripts, not a package, so its directory is put on sys.path here once for
every test module in this package.
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOLS_DIR = os.path.join(REPO, "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)
