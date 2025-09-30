# Ensure src/ is prioritized over project root during tests
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
SRC = os.path.join(ROOT, "src")

# Put SRC first so the src/ package is imported preferentially
if SRC in sys.path:
    sys.path.remove(SRC)
sys.path.insert(0, SRC)

# Then ensure ROOT is available (after SRC)
if ROOT not in sys.path:
    sys.path.insert(1, ROOT)
