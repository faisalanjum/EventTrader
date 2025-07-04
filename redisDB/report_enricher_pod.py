#!/usr/bin/env python3
"""Kubernetes pod version of report enricher"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import and run existing worker function
from redisDB.report_enricher import enrich_worker

if __name__ == "__main__":
    enrich_worker()