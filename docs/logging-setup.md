# Logging Setup Instructions

## Manual Steps Required on Each Node

### 1. Create Log Directories

SSH to each node and run:

**On minisforum2 (192.168.40.72):**
```bash
sudo mkdir -p /home/faisal/EventMarketDB/logs
sudo chown faisal:faisal /home/faisal/EventMarketDB/logs
```

**On minisforum3 (192.168.40.74):**
```bash
sudo mkdir -p /home/faisal/EventMarketDB/logs
sudo chown faisal:faisal /home/faisal/EventMarketDB/logs
```

### 2. Setup Logrotate

Create `/etc/logrotate.d/eventmarketdb` on all nodes (minisforum, minisforum2, minisforum3):

```bash
sudo tee /etc/logrotate.d/eventmarketdb << 'EOF'
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
```

### 3. Test Logrotate Configuration

```bash
sudo logrotate -d /etc/logrotate.d/eventmarketdb
```

## Log File Organization

After setup, logs will be organized as:
- `xbrl-heavy_20250704_minisforum2.log` - All heavy XBRL workers on minisforum2
- `xbrl-medium_20250704_minisforum2.log` - All medium XBRL workers on minisforum2
- `xbrl-light_20250704_minisforum2.log` - All light XBRL workers on minisforum2
- `enricher_20250704_minisforum2.log` - All report enricher pods on minisforum2
- Similar files on minisforum3 with `_minisforum3` suffix

## Collecting Logs from All Nodes

To aggregate logs from all nodes to the control node:

```bash
# Create archive directory
mkdir -p /home/faisal/EventMarketDB/logs/archive

# Sync from minisforum2
rsync -av minisforum2:/home/faisal/EventMarketDB/logs/ /home/faisal/EventMarketDB/logs/archive/minisforum2/

# Sync from minisforum3  
rsync -av minisforum3:/home/faisal/EventMarketDB/logs/ /home/faisal/EventMarketDB/logs/archive/minisforum3/
```