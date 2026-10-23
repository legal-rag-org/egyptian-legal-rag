import os
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from helpers import get_settings

_prev_cwd = os.getcwd()
os.chdir(SRC_DIR)
try:
    settings = get_settings()
finally:
    os.chdir(_prev_cwd)