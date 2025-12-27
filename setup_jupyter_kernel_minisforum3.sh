#!/bin/bash
# Setup Jupyter kernel on minisforum3 for VS Code Remote-SSH

echo "Setting up Jupyter kernel on minisforum3..."
echo "Current host: $(hostname)"

# Navigate to project directory
cd /home/faisal/EventMarketDB

# Activate the virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Check Python path
echo "Python path: $(which python)"
echo "Python version: $(python --version)"

# Install ipykernel if not already installed
echo "Checking for ipykernel..."
if ! python -c "import ipykernel" 2>/dev/null; then
    echo "Installing ipykernel..."
    pip install ipykernel
else
    echo "ipykernel already installed"
fi

# Install the kernel
echo "Installing Jupyter kernel..."
python -m ipykernel install --user --name eventmarketdb --display-name "EventMarketDB (venv)"

# Also create a more specific kernel name
python -m ipykernel install --user --name eventmarketdb-minisforum3 --display-name "EventMarketDB (minisforum3)"

# List installed kernels
echo -e "\nInstalled kernels:"
jupyter kernelspec list

# Create VS Code settings if they don't exist
echo -e "\nCreating VS Code settings..."
mkdir -p /home/faisal/EventMarketDB/.vscode

cat > /home/faisal/EventMarketDB/.vscode/settings.json << 'EOF'
{
    "python.defaultInterpreterPath": "/home/faisal/EventMarketDB/venv/bin/python",
    "jupyter.kernels.filter": [
        {
            "path": "/home/faisal/EventMarketDB/venv/bin/python",
            "type": "pythonEnvironment"
        }
    ]
}
EOF

echo -e "\nSetup complete! Please:"
echo "1. Reload VS Code window (Ctrl+Shift+P -> 'Developer: Reload Window')"
echo "2. Open your notebook"
echo "3. Select kernel 'EventMarketDB (venv)' or 'EventMarketDB (minisforum3)'"