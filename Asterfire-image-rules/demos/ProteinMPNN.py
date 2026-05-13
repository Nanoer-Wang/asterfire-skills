from pathlib import Path
import os

cwd = Path.cwd()
mpnn_dir = cwd / "ProteinMPNN-main"
if not mpnn_dir.is_dir():
    mpnn_dir = cwd
