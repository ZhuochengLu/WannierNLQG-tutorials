#!/usr/bin/env python3
"""List, check or render this chapter's explicitly mapped figures."""
from pathlib import Path
import runpy
import sys
root=Path(__file__).resolve().parents[2]
sys.argv[1:1]=["--chapter",Path(__file__).resolve().parent.name]
runpy.run_path(str(root/"scripts/plot_tutorial.py"),run_name="__main__")
