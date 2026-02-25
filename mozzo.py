#!/usr/bin/env python3
import sys

# Ensure the local 'src' directory is in the python path
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from mozzo.cli import main

if __name__ == "__main__":
    main()
