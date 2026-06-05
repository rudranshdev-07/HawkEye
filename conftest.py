import sys
import os

# Add root path to sys.path to enable smooth imports of 'src' in tests
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
