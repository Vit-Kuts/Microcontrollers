# -*- coding: utf-8 -*-
"""OpenOCD utilities"""

import re
from pathlib import Path
from typing import Optional, Dict, List


# Расширенный словарь соответствия MCU и OpenOCD конфигов
OPENOCD_CONFIG_MAPPING = {
    # F-серия
    'STM32F0': 'target/stm32f0x.cfg',
    'STM32F1': 'target/stm32f1x.cfg',
    'STM32F2': 'target/stm32f2x.cfg',
    'STM32F3': 'target/stm32f3x.cfg',
    'STM32F4': 'target/stm32f4x.cfg',
    'STM32F7': 'target/stm32f7x.cfg',
    # G-серия
    'STM32G0': 'target/stm32g0x.cfg',
    'STM32G4': 'target/stm32g4x.cfg',
    # H-серия
    'STM32H5': 'target/stm32h5x.cfg',
    'STM32H7': 'target/stm32h7x.cfg',
    # L-серия
    'STM32L0': 'target/stm32l0x.cfg',
    'STM32L1': 'target/stm32l1x.cfg',
    'STM32L4': 'target/stm32l4x.cfg',
    'STM32L5': 'target/stm32l5x.cfg',
    # U-серия
    'STM32U5': 'target/stm32u5x.cfg',
    # WB-серия
    'STM32WB': 'target/stm32wbx.cfg',
    # WL-серия
    'STM32WL': 'target/stm32wlx.cfg',
    # MP-серия
    'STM32MP1': 'target/stm32mp1x.cfg',
}


def get_mcu_type_from_ioc(project_root: Path) -> Optional[str]:
    """Extract MCU type from .ioc file"""
    ioc_files = list(project_root.glob("*.ioc"))
    if not ioc_files:
        return None
    
    ioc_file = ioc_files[0]
    print(f"  Found .ioc file: {ioc_file.name}")
    
    with open(ioc_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Ищем MCU в .ioc файле
    match = re.search(r'^MCU=(.*?)$', content, re.MULTILINE)
    if match:
        mcu = match.group(1).strip()
        # Очищаем от лишних символов
        mcu = re.sub(r'[^\w]', '', mcu)
        print(f"  Detected MCU from .ioc: {mcu}")
        return mcu
    
    return None


def get_mcu_type_from_cmakelists(project_root: Path) -> Optional[str]:
    """Extract MCU type from CMakeLists.txt"""
    cmake_file = project_root / "CMakeLists.txt"
    if not cmake_file.exists():
        return None
    
    with open(cmake_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Ищем определение MCU в CMakeLists.txt
    patterns = [
        r'set\s*\(\s*MCU_TYPE\s+([^\s\)]+)',
        r'set\s*\(\s*STM32_MCU\s+([^\s\)]+)',
        r'STM32_MCU_TYPE\s+([^\s\)]+)',
        r'-DSTM32_MCU=([^\s\)]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            mcu = match.group(1).strip()
            mcu = re.sub(r'[^\w]', '', mcu)
            print(f"  Detected MCU from CMakeLists.txt: {mcu}")
            return mcu
    
    return None


def get_mcu_type_from_ld(project_root: Path) -> Optional[str]:
    """Extract MCU type from .ld file"""
    # Ищем .ld файлы в разных местах
    ld_search_paths = [
        project_root,
        project_root / "Debug",
        project_root / "Release",
        project_root / "build" / "Debug",
        project_root / "build" / "Release",
    ]
    
    ld_files = []
    for search_path in ld_search_paths:
        if search_path.exists():
            ld_files.extend(list(search_path.glob("*.ld")))
    
    if not ld_files:
        return None
    
    ld_file = ld_files[0]
    print(f"  Found linker script: {ld_file.name}")
    
    with open(ld_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Паттерны для поиска MCU в .ld файле
    patterns = [
        r'#define\s+STM32(\w+)',
        r'#define\s+(\w+)\s*/\*\s*MCU',
        r'/\*\s*MCU:\s*(\w+)\s*\*/',
        r'/\*\s*Device:\s*([^*]+)\s*\*/',
        r'(\w+)\s*/\*\s*Device',
        r'OUTPUT_ARCH\s*\(\s*"([^"]+)"\s*\)',
        r'GROUP\s*\(\s*[^)]*?([A-Za-z0-9_]+)\.ld',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            mcu = match.group(1).strip()
            # Очищаем MCU
            mcu = re.sub(r'xx$', '', mcu, flags=re.IGNORECASE)
            mcu = re.sub(r'x$', '', mcu, flags=re.IGNORECASE)
            mcu = re.sub(r'_', '', mcu)
            mcu = mcu.upper()
            
            # Проверяем, что это похоже на STM32
            if not mcu.startswith('STM32'):
                # Пытаемся найти STM32 в строке
                stm_match = re.search(r'(STM32\w+)', mcu)
                if stm_match:
                    mcu = stm_match.group(1)
                else:
                    mcu = f'STM32{mcu}'
            
            print(f"  Detected MCU from linker script: {mcu}")
            return mcu
    
    # Пытаемся извлечь из имени файла
    mcu_match = re.search(r'(STM32\w+)', ld_file.name, re.IGNORECASE)
    if mcu_match:
        mcu = mcu_match.group(1).upper()
        mcu = re.sub(r'[Xx]+$', '', mcu)
        print(f"  Detected MCU from filename: {mcu}")
        return mcu
    
    return None


def get_mcu_type_from_cube_project(project_root: Path) -> Optional[str]:
    """Extract MCU type from CubeMX project files"""
    # Проверяем .mxproject файл
    mxproject_file = project_root / ".mxproject"
    if mxproject_file.exists():
        with open(mxproject_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        match = re.search(r'^MCU\s*=\s*([^\n]+)', content, re.MULTILINE)
        if match:
            mcu = match.group(1).strip()
            mcu = re.sub(r'[^\w]', '', mcu)
            print(f"  Detected MCU from .mxproject: {mcu}")
            return mcu
    
    # Проверяем файлы конфигурации
    config_files = list(project_root.glob("*.ioc"))
    for config_file in config_files:
        with open(config_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Ищем другие паттерны
        patterns = [
            r'MCU\s*=\s*([^\s]+)',
            r'Family\s*=\s*([^\s]+)',
            r'Series\s*=\s*([^\s]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                mcu = match.group(1).strip()
                mcu = re.sub(r'[^\w]', '', mcu)
                if mcu.startswith('STM32'):
                    print(f"  Detected MCU from config: {mcu}")
                    return mcu
    
    return None


def get_mcu_type(project_root: Path) -> Optional[str]:
    """Get MCU type from multiple sources with priority"""
    print("\n  Detecting MCU type...")
    
    # Пробуем разные источники по приоритету
    sources = [
        ("CubeMX .ioc file", get_mcu_type_from_ioc),
        ("CubeMX .mxproject file", get_mcu_type_from_cube_project),
        ("CMakeLists.txt", get_mcu_type_from_cmakelists),
        ("Linker script", get_mcu_type_from_ld),
    ]
    
    for source_name, source_func in sources:
        mcu = source_func(project_root)
        if mcu:
            print(f"  [OK] MCU detected from {source_name}: {mcu}")
            return mcu
    
    print("  [FAILED] Could not detect MCU type from any source")
    return None


def get_mcu_family(mcu_type: str) -> Optional[str]:
    """Extract MCU family from MCU type (e.g., STM32F4 from STM32F407)"""
    if not mcu_type:
        return None
    
    mcu_upper = mcu_type.upper()
    
    # Пробуем найти семейство
    match = re.match(r'(STM32[F|G|H|L|U|W|M][A-Z0-9]*)', mcu_upper)
    if match:
        family = match.group(1)
        # Если семейство короткое (например STM32F), добавляем номер
        if len(family) <= 6:
            # Пробуем найти более точное семейство
            match2 = re.match(r'(STM32[F|G|H|L|U|W|M][A-Z0-9]{1,2})', mcu_upper)
            if match2:
                return match2.group(1)
        return family
    
    # Если не нашли, пробуем найти просто STM32
    match = re.search(r'(STM32\w+)', mcu_upper)
    if match:
        return match.group(1)
    
    return None


def find_svd_file(svd_dir: Path, mcu_type: str) -> Optional[str]:
    """Find SVD file for given MCU type with improved search"""
    if not svd_dir.exists():
        print(f"  [WARNING] SVD directory does not exist: {svd_dir}")
        print(f"  [INFO] Set SVD_DIR environment variable to point to your SVD files folder")
        return None
    
    mcu_upper = mcu_type.upper()
    svd_files = list(svd_dir.rglob("*.svd"))
    
    if not svd_files:
        print(f"  [WARNING] No SVD files found in {svd_dir}")
        return None
    
    print(f"  Found {len(svd_files)} SVD files")
    
    # Получаем семейство MCU
    mcu_family = get_mcu_family(mcu_upper)
    print(f"  MCU family: {mcu_family}")
    
    # Список паттернов для поиска в порядке приоритета
    search_patterns = [
        mcu_upper,  # Точное совпадение (STM32F407)
        mcu_family,  # Семейство (STM32F4)
        mcu_upper.replace('STM32', 'STM32_'),  # С подчеркиванием (STM32F407)
        re.sub(r'(\d+)$', r'x\1', mcu_upper),  # С x вместо последней цифры (STM32F40x)
    ]
    
    # Убираем дубликаты и None
    search_patterns = list(set([p for p in search_patterns if p]))
    
    # Ищем по всем паттернам
    for pattern in search_patterns:
        for svd_file in svd_files:
            svd_name = svd_file.name.upper()
            if pattern in svd_name or pattern.replace('STM32', '') in svd_name:
                print(f"  [OK] Found SVD: {svd_file.name} (matched: {pattern})")
                return str(svd_file)
    
    # Если не нашли, показываем доступные SVD файлы для справки
    print(f"  [WARNING] No matching SVD file found for {mcu_type}")
    print(f"  [INFO] Available SVD files in {svd_dir}:")
    for svd_file in sorted(svd_files)[:5]:
        print(f"    - {svd_file.name}")
    if len(svd_files) > 5:
        print(f"    ... and {len(svd_files) - 5} more")
    
    return None


def get_openocd_target_config(mcu_type: str) -> str:
    """Get OpenOCD target config based on MCU type with fallback"""
    if not mcu_type:
        print(f"  [WARNING] MCU type not detected, using default target")
        return "target/stm32f1x.cfg"
    
    mcu_upper = mcu_type.upper()
    mcu_family = get_mcu_family(mcu_upper)
    
    print(f"  Detected MCU family: {mcu_family}")
    
    # Пробуем найти точное соответствие
    for series, config in OPENOCD_CONFIG_MAPPING.items():
        if mcu_upper.startswith(series):
            print(f"  [OK] Selected OpenOCD target: {config} (matched: {series})")
            return config
        
        # Пробуем по семейству
        if mcu_family and mcu_family.startswith(series):
            print(f"  [OK] Selected OpenOCD target: {config} (matched family: {series})")
            return config
    
    # Если не нашли, пробуем найти по частичному совпадению
    for series, config in OPENOCD_CONFIG_MAPPING.items():
        # Проверяем, содержит ли MCU серию
        if series in mcu_upper:
            print(f"  [OK] Selected OpenOCD target: {config} (partial match: {series})")
            return config
    
    print(f"  [WARNING] Unknown MCU type: {mcu_type}, using default target")
    return "target/stm32f1x.cfg"


def get_interface_config(openocd_scripts: str, debugger_type: str = "stlink") -> str:
    """Get available interface config with support for different debuggers"""
    if not openocd_scripts:
        print(f"  [WARNING] OPENOCD_SCRIPTS not set, using default interface")
        return "interface/stlink.cfg"
    
    scripts_path = Path(openocd_scripts)
    
    if not scripts_path.exists():
        print(f"  [WARNING] OpenOCD scripts directory does not exist: {scripts_path}")
        return "interface/stlink.cfg"
    
    # Поддерживаемые интерфейсы в порядке приоритета
    interface_configs = {
        "stlink": [
            "interface/stlink.cfg",
            "interface/stlink-v2.cfg",
            "interface/stlink-v3.cfg",
        ],
        "jlink": [
            "interface/jlink.cfg",
        ],
        "ftdi": [
            "interface/ftdi/olimex-arm-usb-ocd.cfg",
            "interface/ftdi/olimex-arm-usb-tiny-h.cfg",
        ],
    }
    
    # Выбираем список интерфейсов для указанного типа отладчика
    config_list = interface_configs.get(debugger_type, interface_configs["stlink"])
    
    for config in config_list:
        if (scripts_path / config).exists():
            print(f"  [OK] Found interface config: {config}")
            return config
    
    # Если не нашли, пробуем stlink как fallback
    for config in interface_configs["stlink"]:
        if (scripts_path / config).exists():
            print(f"  [OK] Found interface config (fallback): {config}")
            return config
    
    print(f"  [WARNING] No interface config found in {scripts_path}")
    return "interface/stlink.cfg"