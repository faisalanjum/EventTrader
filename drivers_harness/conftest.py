"""Pytest bootstrap — put the harness dir on sys.path so tests import the
core modules (driver_ids, vocab_seed, ...) by bare name."""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
