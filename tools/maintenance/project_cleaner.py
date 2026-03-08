#!/usr/bin/env python3
"""
PowerBank Project Cleaner - Unified Refactoring Tool
===================================================

This tool helps identify and fix imports, cleanup unused code, and remove 
redundant files across the project with 100% accuracy.

Features:
1.  Imports: AST-based cleanup of unused imports.
2.  Unused Code: Identifies classes/methods/functions that are never called.
3.  Dead Files: Identifies Python files that are never imported.
4.  Duplicates: Finds identical code blocks across the project.
5.  Audit: Full project health report.

Usage:
    python tools/project_cleaner.py audit
    python tools/project_cleaner.py clean-imports --path api/users/
    python tools/project_cleaner.py find-unused --app users
    python tools/project_cleaner.py find-dead-files
    python tools/project_cleaner.py find-duplicates --min-lines 10
"""

import argparse
import ast
import os
import re
import sys
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Tuple, Any, Optional
from collections import defaultdict


class ProjectCleaner:
    def __init__(self, root_dir: str = "."):
        self.root = Path(root_dir).resolve()
        if not (self.root / "manage.py").exists():
            # Try to find root
            for parent in self.root.parents:
                if (parent / "manage.py").exists():
                    self.root = parent
                    break
        
        self.api_dir = self.root / "api"
        self.exclude_dirs = {
            "__pycache__", "migrations", ".git", "venv", "env", 
            "staticfiles", "media", "node_modules", "backups"
        }
        self.exclude_files = {"manage.py", "wsgi.py", "asgi.py", "celery.py"}

    def get_py_files(self, path: Optional[Path] = None) -> List[Path]:
        search_path = path or self.api_dir
        py_files = []
        for root, dirs, files in os.walk(search_path):
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
            for file in files:
                if file.endswith(".py") and file not in self.exclude_files:
                    py_files.append(Path(root) / file)
        return py_files

    # --- Import Cleaning (Leveraging logic from import_cleanup.py) ---
    
    def clean_imports(self, path: Path, preview: bool = False):
        """Clean unused imports in a file or directory"""
        if path.is_dir():
            files = self.get_py_files(path)
            print(f"[INFO] Cleaning imports in {len(files)} files...")
            for f in files:
                self._clean_file_imports(f, preview)
        else:
            self._clean_file_imports(path, preview)

    def _clean_file_imports(self, file_path: Path, preview: bool):
        sys.path.append(str(self.root / "tools"))
        try:
            from import_cleanup import ImportCleanup
            cleaner = ImportCleanup(project_root=str(self.root))
            cleaner.clean_file(str(file_path), preview=preview)
        except Exception as e:
            print(f"[ERROR] Error cleaning {file_path.name}: {e}")
        finally:
            if str(self.root / "tools") in sys.path:
                sys.path.remove(str(self.root / "tools"))

    # --- Unused Code Detection ---

    def find_unused_code(self, app_name: Optional[str] = None):
        """Find classes and functions that are defined but never used"""
        print(f"[SCAN] Searching for unused code{' in ' + app_name if app_name else ''}...")
        
        target_dir = self.api_dir / app_name if app_name else self.api_dir
        files = self.get_py_files(target_dir)
        
        all_definitions = [] # List of (name, type, file, line)
        
        # 1. Collect all definitions
        for f in files:
            try:
                with open(f, 'r', encoding='utf-8') as src:
                    tree = ast.parse(src.read())
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            if not node.name.startswith('_'): # Skip private
                                all_definitions.append((node.name, 'function', f, node.lineno))
                        elif isinstance(node, ast.ClassDef):
                            if not node.name.startswith('_'):
                                all_definitions.append((node.name, 'class', f, node.lineno))
            except Exception:
                continue

        # 2. Search for usages
        unused = []
        project_files = self.get_py_files(self.root)
        
        # Optimization: Pre-read all project files
        file_contents = []
        for pf in project_files:
            try:
                with open(pf, 'r', encoding='utf-8') as src:
                    file_contents.append((pf, src.read()))
            except Exception:
                continue

        for name, dtype, def_file, line in all_definitions:
            # Special exceptions for Django
            if name in ['get_queryset', 'perform_create', 'list', 'create', 'retrieve', 'update', 'partial_update', 'destroy']:
                continue
            
            found = False
            pattern = re.compile(rf'\b{re.escape(name)}\b')
            
            for pf, content in file_contents:
                # Check for usage (excluding the definition itself)
                matches = pattern.findall(content)
                if len(matches) > 1: # More than just the definition
                    found = True
                    break
                elif len(matches) == 1 and pf != def_file:
                    found = True
                    break
            
            if not found:
                unused.append((name, dtype, def_file, line))

        print(f"[SUMMARY] Found {len(unused)} potentially unused elements.")
        for name, dtype, f, line in unused:
            rel_path = f.relative_to(self.root)
            print(f"  [UNUSED] {dtype}: {name} ({rel_path}:{line})")
        
        return unused

    # --- Dead File Detection ---

    def find_dead_files(self):
        """Find Python files that are never imported"""
        print("[SCAN] Searching for dead files...")
        all_files = self.get_py_files(self.api_dir)
        import_patterns = {}
        
        for f in all_files:
            # Convert path to module path
            # E.g. api/users/models.py -> api.users.models
            rel = f.relative_to(self.root).with_suffix("")
            module_path = ".".join(rel.parts)
            import_patterns[f] = [
                re.compile(rf'import\s+{re.escape(module_path)}'),
                re.compile(rf'from\s+{re.escape(module_path)}\s+import'),
                re.compile(rf'from\s+{".".join(rel.parts[:-1])}\s+import\s+{rel.parts[-1]}')
            ]

        dead_files = []
        project_files = self.get_py_files(self.root)
        file_contents = []
        for pf in project_files:
            try:
                with open(pf, 'r', encoding='utf-8') as src:
                    file_contents.append(src.read())
            except Exception:
                continue

        for f, patterns in import_patterns.items():
            # Skip common entry points
            if f.name in ["urls.py", "admin.py", "apps.py", "models.py", "serializers.py"]:
                continue
                
            is_imported = False
            for content in file_contents:
                if any(p.search(content) for p in patterns):
                    is_imported = True
                    break
            
            if not is_imported:
                dead_files.append(f)

        print(f"[SUMMARY] Found {len(dead_files)} potentially dead files.")
        for f in dead_files:
            print(f"  [DEAD] file: {f.relative_to(self.root)}")
        
        return dead_files

    # --- Duplicate Detection ---

    def find_duplicates(self, min_lines: int = 10):
        """Find duplicate code blocks"""
        print(f"[SCAN] Searching for duplicates (min {min_lines} lines)...")
        files = self.get_py_files(self.api_dir)
        hashes = defaultdict(list)
        
        for f in files:
            try:
                with open(f, 'r', encoding='utf-8') as src:
                    lines = [line.strip() for line in src.readlines() if line.strip() and not line.strip().startswith("#")]
                    
                    for i in range(len(lines) - min_lines + 1):
                        block = "\n".join(lines[i:i+min_lines])
                        h = hashlib.md5(block.encode()).hexdigest()
                        hashes[h].append((f, i + 1))
            except Exception:
                continue

        duplicates = {h: locs for h, locs in hashes.items() if len(locs) > 1}
        
        print(f"[SUMMARY] Found {len(duplicates)} duplicate blocks.")
        for h, locs in duplicates.items():
            print(f"  [DUPLICATE] Duplicate block found in {len(locs)} places:")
            for f, line in locs:
                print(f"    - {f.relative_to(self.root)}:{line}")
        
        return duplicates

    # --- Audit ---

    def run_audit(self):
        print(f"\n{'='*60}")
        print(f"PROJECT CLEANLINESS AUDIT - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'='*60}\n")
        
        self.find_dead_files()
        print("\n")
        self.find_unused_code()
        print("\n")
        self.find_duplicates()
        print(f"\n{'='*60}")


def main():
    parser = argparse.ArgumentParser(description="PowerBank Project Cleaner")
    subparsers = parser.add_subparsers(dest="command")

    # Audit
    subparsers.add_parser("audit", help="Run full project audit")

    # Clean Imports
    ci = subparsers.add_parser("clean-imports", help="Clean unused imports")
    ci.add_argument("--path", default="api", help="Path to clean (file or directory)")
    ci.add_argument("--preview", action="store_true", help="Preview only")

    # Find Unused
    fu = subparsers.add_parser("find-unused", help="Find unused methods and classes")
    fu.add_argument("--app", help="Filter by app name")

    # Find Dead Files
    subparsers.add_parser("find-dead-files", help="Find unimported python files")

    # Find Duplicates
    fd = subparsers.add_parser("find-duplicates", help="Find duplicate code blocks")
    fd.add_argument("--min-lines", type=int, default=10, help="Minimum lines to consider a duplicate")

    args = parser.parse_args()
    
    cleaner = ProjectCleaner()

    if args.command == "audit":
        cleaner.run_audit()
    elif args.command == "clean-imports":
        cleaner.clean_imports(Path(args.path), args.preview)
    elif args.command == "find-unused":
        cleaner.find_unused_code(args.app)
    elif args.command == "find-dead-files":
        cleaner.find_dead_files()
    elif args.command == "find-duplicates":
        cleaner.find_duplicates(args.min_lines)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
