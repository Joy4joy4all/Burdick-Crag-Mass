# TITS Production System 
# C:\TITS\TITS_Production\__init__.py

from pathlib import Path
import sys
import os

ROOT = Path(__file__).parent

# 1. Align Imports with the physical layout: Ensure TITS_Production is visible
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

def initialize_environment():
    """
    Initializes the GIBUSH environment, ensuring centralized theme, logging, 
    and module paths are set before running any application logic.
    """
    print("Initializing TITS Production environment (GIBUSH)...")
    
    # Imports now work relative to the project root (TITS_Production)
    # 2. Centralize common UI behavior: Theme setup
    from core.hmi_theme import apply_dark_theme
    
    # 3. Centralize common logger (assuming TITSLogger is defined in core/)
    # from core.tits_logger import init_logging # Assuming this path/module exists in your structure
    
    # Execute environment configurations
    apply_dark_theme()
    # init_logging() 
    
    print("Environment Initialization complete.")

# NOTE: No code should run here directly; it must be called by the application entry point.