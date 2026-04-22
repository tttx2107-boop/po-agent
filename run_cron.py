#!/usr/bin/env python3
"""定时任务入口"""
import sys
sys.path.insert(0, '.')

from src.entry.cron import main

if __name__ == "__main__":
    sys.exit(main())
