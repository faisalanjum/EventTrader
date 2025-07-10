# Key Changes in kubeSetup.md Update

## Major Corrections

### 1. XBRL Light Worker Memory (CRITICAL)
- **OLD**: 3GB RAM request
- **ACTUAL**: 1.5GB RAM (1536Mi)
- **Impact**: Saves 1.5GB per pod × 7 pods = 10.5GB at max scale

### 2. KEDA Configuration
- **OLD**: minReplicaCount: 0
- **NEW**: minReplicaCount: 1 for all workers
- **Reason**: Fixed KEDA activation issues, ensures instant processing

### 3. Max Replica Counts
- **Document claimed**: Heavy=2, Medium=2, Light=3 (7 total)
- **Actually implemented**: Heavy=2, Medium=4, Light=7 (13 total)
- **Current**: Keeping actual implementation

### 4. Neo4j Memory
- **Document**: Reduce to 85GB
- **Actually implemented**: 90GB
- **Current usage**: ~35GB (plenty of headroom)

### 5. Node Memory (Accurate Conversion)
- **minisforum**: 57.51GB (not 57GB)
- **minisforum2**: 60.51GB (not 60GB)
- **minisforum3**: 123.51GB (not 126GB)

### 6. Node Taints
- **Document**: Keep graph taint on minisforum
- **Actually**: ALL taints removed from minisforum
- **minisforum3**: Still has database=neo4j:NoSchedule

## Resource Calculation Corrections

### Old Document (Incorrect)
- Light workers: 3 pods × 3GB = 9GB
- Total XBRL at 7-pod limit: 45GB

### Actual Current Configuration
- Light workers: 7 pods × 1.5GB = 10.5GB  
- Total XBRL at max scale: 52.5GB
- Total XBRL at min scale: 20.5GB

### Impact on Historical Processing
- **Available on minisforum**: 54.2GB (more than enough)
- **Historical needs**: 48GB
- **Buffer**: 6.2GB

## Why These Changes Matter

1. **More realistic resource planning** - Based on actual kubectl output
2. **KEDA reliability** - minReplicas=1 prevents activation issues
3. **Better scaling headroom** - Can scale to 13 XBRL pods vs 7
4. **Accurate math** - All calculations verified against real data

The updated document now reflects the TRUE state of the cluster.