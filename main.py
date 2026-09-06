"""Entry point: python main.py [--root DATA_DIR] [--lang zh|en]"""
import argparse
from pathlib import Path

from iconmatch import i18n
from iconmatch.app import main
from iconmatch.database import DEFAULT_ROOT

if __name__ == "__main__":
    i18n.load_language()
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT,
                    help=i18n.t("main.help.root"))
    ap.add_argument("--lang", choices=sorted(i18n.LANGUAGES),
                    help=i18n.t("cli.help.lang"))
    args = ap.parse_args()
    main(args.root, args.lang)
