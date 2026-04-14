# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""Test what's breaking in validation_test_collector.py"""

import sys
import traceback

try:
    print("Testing imports...")
    from PySide6.QtWidgets import QApplication
    print("✓ PySide6")
    
    import torch
    print("✓ PyTorch")
    
    import numpy as np
    print("✓ NumPy")
    
    print("\nTesting module load...")
    import validation_test_collector
    print("✓ Module loaded")
    
    print("\nTesting app creation...")
    app = QApplication(sys.argv)
    print("✓ QApplication created")
    
    print("\nTesting main window...")
    window = validation_test_collector.BCMTestCollector()
    print("✓ Main window created")
    
    print("\n✓✓✓ ALL TESTS PASSED - App should work")
    
except Exception as e:
    print(f"\n✗✗✗ ERROR FOUND:")
    print(f"{type(e).__name__}: {e}")
    print("\nFull traceback:")
    traceback.print_exc()
