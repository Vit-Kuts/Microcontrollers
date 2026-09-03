# -*- coding: utf-8 -*-
"""Configuration generation modules for VSCode"""

from .launch_json import generate_launch_json
from .tasks_json import generate_tasks_json
from .c_cpp_properties import generate_c_cpp_properties
from .settings import generate_settings

__all__ = [
    'generate_launch_json',
    'generate_tasks_json',
    'generate_c_cpp_properties',
    'generate_settings'
]