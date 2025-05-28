#/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Main entry point for NetWORKS application
"""

import sys
from src.app import Application

if __name__ == "__main__":
    app = Application(sys.argv)
    sys.exit(app.run())
