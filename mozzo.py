#!/usr/bin/env python3
import sys
import os

# Ensure the local 'src' directory is in the python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from mozzo.cli import main  # noqa: E402

if __name__ == "__main__":
    main()
