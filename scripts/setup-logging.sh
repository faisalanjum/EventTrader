#!/bin/bash

# Setup logging directories and logrotate on all nodes
# Run this script from the control node (minisforum)

echo "Setting up logging infrastructure..."

# Function to setup node
setup_node() {
    local node=$1
    local ip=$2
    echo "Setting up $node ($ip)..."
    
    # Create directory
    ssh faisal@$ip "sudo mkdir -p /home/faisal/EventMarketDB/logs && sudo chown faisal:faisal /home/faisal/EventMarketDB/logs"
    
    # Setup logrotate
    ssh faisal@$ip 'sudo tee /etc/logrotate.d/eventmarketdb > /dev/null << EOF
/home/faisal/EventMarketDB/logs/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    copytruncate
    create 0644 faisal faisal
}
EOF'
    
    # Test logrotate
    ssh faisal@$ip "sudo logrotate -d /etc/logrotate.d/eventmarketdb 2>&1 | grep -E '(considering|rotating)' | head -5"
    
    echo "✓ $node setup complete"
}

# Setup on local node first
echo "Setting up minisforum (local)..."
sudo mkdir -p /home/faisal/EventMarketDB/logs
sudo chown faisal:faisal /home/faisal/EventMarketDB/logs

sudo tee /etc/logrotate.d/eventmarketdb > /dev/null << 'EOF'
/home/faisal/EventMarketDB/logs/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    copytruncate
    create 0644 faisal faisal
}
EOF

echo "✓ minisforum (local) setup complete"

# Setup remote nodes
setup_node "minisforum2" "192.168.40.72"
setup_node "minisforum3" "192.168.40.74"

echo "
Logging setup complete! To verify:
1. Check pod logs are being written: kubectl logs -n processing <pod-name>
2. Check file logs on nodes: ls -la /home/faisal/EventMarketDB/logs/
3. Test log aggregation: rsync -av minisforum2:/home/faisal/EventMarketDB/logs/ /home/faisal/EventMarketDB/logs/archive/minisforum2/
"