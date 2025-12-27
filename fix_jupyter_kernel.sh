#!/bin/bash
# Quick fix for VS Code Jupyter kernel visibility issues

echo "Fixing Jupyter kernel visibility..."

# Clear caches
echo "1. Clearing caches..."
rm -rf ~/.cache/ms-python* ~/.cache/jupyter* 2>/dev/null

# Re-register kernel
echo "2. Re-registering EventMarketDB kernel..."
source /home/faisal/EventMarketDB/venv/bin/activate
python -m ipykernel install --user --name eventmarketdb --display-name "EventMarketDB (venv)" --force

# Kill stale Jupyter processes
echo "3. Cleaning up stale processes..."
pkill -f "jupyter-kernel" 2>/dev/null

# List kernels
echo -e "\n4. Available kernels:"
jupyter kernelspec list

echo -e "\nDone! Now:"
echo "- Reload VS Code window (Ctrl+Shift+P -> 'Developer: Reload Window')"
echo "- Open your notebook and select 'EventMarketDB (venv)' kernel"