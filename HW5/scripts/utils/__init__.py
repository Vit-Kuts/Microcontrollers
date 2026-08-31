# -*- coding: utf-8 -*-
"""Utility modules for project detection and OpenOCD"""

from .file_utils import get_project_root, ensure_directory, get_project_name
from .openocd_utils import (
    get_mcu_type,
    get_mcu_family,
    find_svd_file,
    get_openocd_target_config,
    get_interface_config
)

__all__ = [
    'get_project_root',
    'ensure_directory',
    'get_project_name',
    'get_mcu_type',
    'get_mcu_family',
    'find_svd_file',
    'get_openocd_target_config',
    'get_interface_config'
]