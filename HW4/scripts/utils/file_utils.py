# -*- coding: utf-8 -*-
"""File and directory utilities"""

import os
import re
from pathlib import Path
from typing import Optional


def get_project_root() -> Path:
    """Get project root directory (where .ioc file is located)"""
    current_dir = Path(__file__).resolve().parent.parent.parent  # scripts/utils/ -> project root
    
    # If script is in scripts folder, project root is parent of scripts
    if current_dir.name == 'scripts':
        return current_dir.parent
    
    # Look for .ioc file
    for parent in [current_dir] + list(current_dir.parents):
        ioc_files = list(parent.glob("*.ioc"))
        if ioc_files:
            return parent
    
    # Fallback: use current directory
    print(f"Warning: Could not find project root, using {current_dir}")
    return current_dir


def ensure_directory(directory: Path) -> bool:
    """Create directory if it doesn't exist"""
    if not directory.exists():
        try:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"[INFO] Created directory: {directory}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to create directory: {e}")
            return False
    else:
        print(f"[INFO] Directory already exists: {directory}")
        return True


def get_project_name(project_root: Path) -> str:
    """Get project name from .ioc file or CMakeLists.txt"""
    # Try to get from .ioc file
    ioc_files = list(project_root.glob("*.ioc"))
    if ioc_files:
        return ioc_files[0].stem
    
    # Try CMakeLists.txt
    cmake_file = project_root / "CMakeLists.txt"
    if cmake_file.exists():
        with open(cmake_file, 'r', encoding='utf-8') as f:
            content = f.read()
            match = re.search(r'project\((\w+)\s', content)
            if match:
                return match.group(1)
    
    return project_root.name