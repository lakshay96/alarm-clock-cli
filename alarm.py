#!/usr/bin/env python3
"""Entry point: `python alarm.py <command>`."""
import sys

from alarm_clock.cli import main

if __name__ == "__main__":
    sys.exit(main())
