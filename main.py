"""Entry point: python main.py [--root DATA_DIR]"""
import argparse
from pathlib import Path

from iconmatch.app import main
from iconmatch.database import DEFAULT_ROOT

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT,
                    help="folder that holds the db_XXX directories")
    main(ap.parse_args().root)
