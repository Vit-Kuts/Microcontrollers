# -*- coding: utf-8 -*-
"""
Script to automatically add/update user .c files and include directories from src folder
- Adds .c files from src and its subdirectories
- Adds include directories from src and its subdirectories (where .h files are located)
- Does NOT touch STM32CubeMX generated files
"""

import os
import re
import sys
from pathlib import Path
from typing import Set, List

def find_c_files(src_dir: Path, project_root: Path) -> Set[str]:
    """Find all .c files in src directory and its subdirectories"""
    c_files = set()
    
    if not src_dir.exists():
        print(f"Warning: {src_dir} directory does not exist")
        return c_files
    
    for c_file in src_dir.rglob("*.c"):
        # Use relative path from project root
        rel_path = c_file.relative_to(project_root).as_posix()
        c_files.add(rel_path)
    
    return c_files

def find_include_dirs(src_dir: Path, project_root: Path) -> Set[str]:
    """Find all directories in src that contain .h files"""
    include_dirs = set()
    
    if not src_dir.exists():
        return include_dirs
    
    # Add src directory itself
    include_dirs.add("src")
    
    # Find all subdirectories that contain .h files
    for h_file in src_dir.rglob("*.h"):
        dir_path = h_file.parent
        rel_path = dir_path.relative_to(project_root).as_posix()
        include_dirs.add(rel_path)
    
    return include_dirs

def get_current_user_c_files(cmake_file: Path) -> Set[str]:
    """Extract current user .c files from CMakeLists.txt target_sources block"""
    if not cmake_file.exists():
        return set()
    
    with open(cmake_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find target_sources block
    pattern = r'target_sources\(\$\{CMAKE_PROJECT_NAME\} PRIVATE\n(.*?)\n\)'
    match = re.search(pattern, content, re.DOTALL)
    
    if not match:
        return set()
    
    sources_content = match.group(1)
    c_files = set()
    
    for line in sources_content.split('\n'):
        line = line.strip()
        # Look for .c files that are in src directory (user files)
        if '.c' in line and 'src/' in line and line.endswith('.c'):
            # Remove any trailing comments
            if '#' in line:
                line = line[:line.index('#')]
            line = line.strip().strip('"')
            if line and line.endswith('.c'):
                c_files.add(line)
    
    return c_files

def get_current_user_include_dirs(cmake_file: Path) -> Set[str]:
    """Extract current user include directories from CMakeLists.txt"""
    if not cmake_file.exists():
        return set()
    
    with open(cmake_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find target_include_directories block
    pattern = r'target_include_directories\(\$\{CMAKE_PROJECT_NAME\} PRIVATE\n(.*?)\n\)'
    match = re.search(pattern, content, re.DOTALL)
    
    if not match:
        return set()
    
    includes_content = match.group(1)
    include_dirs = set()
    
    for line in includes_content.split('\n'):
        line = line.strip()
        # Only collect src-related include directories
        if line and not line.startswith('#') and 'src' in line:
            path = line.split('#')[0].strip().strip('"')
            if path and path.startswith('src'):
                include_dirs.add(path)
    
    return include_dirs

def update_cmake_lists(cmake_file: Path, current_c_files: Set[str], new_c_files: Set[str],
                      current_inc_dirs: Set[str], new_inc_dirs: Set[str]) -> bool:
    """Update CMakeLists.txt with user .c files and include directories"""
    
    if not cmake_file.exists():
        print(f"Error: {cmake_file} not found")
        return False
    
    # Read current content
    with open(cmake_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Calculate changes
    files_to_add = new_c_files - current_c_files
    files_to_remove = current_c_files - new_c_files
    dirs_to_add = new_inc_dirs - current_inc_dirs
    dirs_to_remove = current_inc_dirs - new_inc_dirs
    
    if not files_to_add and not files_to_remove and not dirs_to_add and not dirs_to_remove:
        print("No changes needed. All user files are synchronized.")
        return True
    
    # Update target_sources block
    content = update_target_sources(content, new_c_files)
    
    # Update target_include_directories block
    content = update_target_includes(content, new_inc_dirs)
    
    # Write updated content
    with open(cmake_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # Print summary
    print_summary(files_to_add, files_to_remove, dirs_to_add, dirs_to_remove, 
                  len(new_c_files), len(new_inc_dirs))
    
    return True

def update_target_sources(content: str, c_files: Set[str]) -> str:
    """Update only the user sources part in target_sources block"""
    
    pattern = r'(target_sources\(\$\{CMAKE_PROJECT_NAME\} PRIVATE\n)(.*?)(\n\))'
    
    def replacer(match):
        existing_content = match.group(2)
        lines = existing_content.split('\n')
        
        new_lines = []
        user_section_started = False
        user_section_ended = False
        
        for line in lines:
            # Find the user sources comment
            if '# Add user sources here' in line:
                new_lines.append(line)
                user_section_started = True
                # Add all user .c files
                for c_file in sorted(c_files):
                    new_lines.append(f"    {c_file}")
                continue
            
            # If we're in user section and hit an empty line or comment line, end section
            if user_section_started and not user_section_ended:
                if line.strip() == '' or (line.strip().startswith('#') and 'Add user sources' not in line):
                    user_section_ended = True
                    new_lines.append(line)
                # Skip old .c file lines
                elif '.c' in line and 'src/' in line:
                    continue
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        
        return match.group(1) + '\n'.join(new_lines) + match.group(3)
    
    return re.sub(pattern, replacer, content, flags=re.DOTALL)

def update_target_includes(content: str, include_dirs: Set[str]) -> str:
    """Update only the user includes part in target_include_directories block"""
    
    pattern = r'(target_include_directories\(\$\{CMAKE_PROJECT_NAME\} PRIVATE\n)(.*?)(\n\))'
    
    def replacer(match):
        existing_content = match.group(2)
        lines = existing_content.split('\n')
        
        new_lines = []
        user_section_started = False
        user_section_ended = False
        
        for line in lines:
            # Find the user includes comment
            if '# Add user defined include paths' in line:
                new_lines.append(line)
                user_section_started = True
                # Add all user include directories
                for inc_dir in sorted(include_dirs):
                    new_lines.append(f"    {inc_dir}")
                continue
            
            # If we're in user section and hit an empty line or comment line, end section
            if user_section_started and not user_section_ended:
                if line.strip() == '' or (line.strip().startswith('#') and 'Add user defined' not in line):
                    user_section_ended = True
                    new_lines.append(line)
                # Skip old include lines that start with src
                elif line.strip().startswith('src'):
                    continue
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        
        return match.group(1) + '\n'.join(new_lines) + match.group(3)
    
    return re.sub(pattern, replacer, content, flags=re.DOTALL)

def print_summary(files_to_add: Set[str], files_to_remove: Set[str],
                 dirs_to_add: Set[str], dirs_to_remove: Set[str],
                 total_files: int, total_dirs: int):
    """Print summary of changes"""
    
    print("\n" + "=" * 60)
    print("USER SOURCES SYNCHRONIZATION SUMMARY")
    print("=" * 60)
    
    if files_to_add:
        print(f"\n[ADDED] C files ({len(files_to_add)}):")
        for f in sorted(files_to_add):
            print(f"  + {f}")
    
    if files_to_remove:
        print(f"\n[REMOVED] C files ({len(files_to_remove)}):")
        for f in sorted(files_to_remove):
            print(f"  - {f}")
    
    if dirs_to_add:
        print(f"\n[ADDED] Include directories ({len(dirs_to_add)}):")
        for d in sorted(dirs_to_add):
            print(f"  + {d}")
    
    if dirs_to_remove:
        print(f"\n[REMOVED] Include directories ({len(dirs_to_remove)}):")
        for d in sorted(dirs_to_remove):
            print(f"  - {d}")
    
    print("\n" + "=" * 60)
    print(f"TOTALS:")
    print(f"  - User .c files: {total_files}")
    print(f"  - User include directories: {total_dirs}")
    print("=" * 60)

def main():
    try:
        # Get project root (parent of scripts folder)
        script_path = Path(__file__).resolve()
        project_root = script_path.parent.parent
        
        src_dir = project_root / "src"
        cmake_file = project_root / "CMakeLists.txt"
        
        print("=" * 60)
        print("STM32 User Sources Synchronization")
        print("=" * 60)
        print(f"Project root: {project_root}")
        print(f"Source directory: {src_dir}")
        print(f"CMakeLists.txt: {cmake_file}")
        print("-" * 60)
        
        # Create src directory if it doesn't exist
        if not src_dir.exists():
            print(f"Creating src directory: {src_dir}")
            src_dir.mkdir(parents=True, exist_ok=True)
        
        # Find user files
        new_c_files = find_c_files(src_dir, project_root)
        new_inc_dirs = find_include_dirs(src_dir, project_root)
        
        print(f"Found {len(new_c_files)} user .c file(s)")
        print(f"Found {len(new_inc_dirs)} user include directorie(s)")
        
        if new_inc_dirs:
            print("\nInclude directories:")
            for inc_dir in sorted(new_inc_dirs):
                print(f"  - {inc_dir}")
        
        # Get current user files from CMakeLists.txt
        current_c_files = get_current_user_c_files(cmake_file)
        current_inc_dirs = get_current_user_include_dirs(cmake_file)
        
        # Update CMakeLists.txt
        if update_cmake_lists(cmake_file, current_c_files, new_c_files, 
                             current_inc_dirs, new_inc_dirs):
            print("\n[SUCCESS] CMakeLists.txt has been updated!")
            return 0
        else:
            print("\n[FAILED] Failed to update CMakeLists.txt")
            return 1
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())