import os
import sys

# Get the absolute path of the project root directory
root_dir = os.path.dirname(os.path.abspath(__file__))

# Add the root directory to Python path if it's not already there
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)