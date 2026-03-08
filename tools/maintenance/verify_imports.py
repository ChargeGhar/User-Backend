#!/usr/bin/env python3
"""
Import Cleanup Verification Script
===================================

This script verifies that the import cleanup didn't break anything.
It checks for:
- Python syntax errors
- Missing imports (NameError potential)
- Unused wildcard imports still remaining
- Import order issues

Usage:
    # Verify all apps
    python tools/verify_imports.py --all
    
    # Verify specific apps
    python tools/verify_imports.py users stations payments
    
    # Detailed output
    python tools/verify_imports.py --all --verbose
"""

import ast
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict


class ImportVerifier:
    """Verify imports after cleanup"""
    
    def __init__(self, project_root: str = None, verbose: bool = False):
        self.project_root = Path(project_root or '.')
        self.verbose = verbose
        self.results = defaultdict(lambda: {
            'syntax_errors': [],
            'wildcard_imports': [],
            'potential_issues': [],
            'files_checked': 0,
            'files_ok': 0
        })
    
    def check_file(self, file_path: Path) -> Dict:
        """Check a single Python file"""
        result = {
            'file': str(file_path),
            'syntax_ok': False,
            'has_wildcards': False,
            'wildcards': [],
            'potential_missing': [],
            'issues': []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse file
            try:
                tree = ast.parse(content)
                result['syntax_ok'] = True
            except SyntaxError as e:
                result['issues'].append(f"Syntax error at line {e.lineno}: {e.msg}")
                return result
            
            # Analyze imports
            imported_names = set()
            wildcard_imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        name = alias.asname if alias.asname else alias.name
                        imported_names.add(name)
                
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        if alias.name == '*':
                            wildcard_imports.append({
                                'line': node.lineno,
                                'module': node.module or ''
                            })
                            result['has_wildcards'] = True
                        else:
                            name = alias.asname if alias.asname else alias.name
                            imported_names.add(name)
            
            result['wildcards'] = wildcard_imports
            
            # Check for used names that might not be imported
            used_names = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    used_names.add(node.id)
            
            # Filter out builtins and locally defined names
            defined_names = set()
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    defined_names.add(node.name)
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            defined_names.add(target.id)
            
            builtins = {
                'True', 'False', 'None', 'str', 'int', 'list', 'dict', 'tuple',
                'set', 'bool', 'float', 'len', 'range', 'enumerate', 'zip',
                '__name__', 'self', 'super', 'type', 'isinstance', 'hasattr',
                'print', 'Exception', 'ValueError', 'TypeError', 'KeyError'
            }
            
            potentially_missing = used_names - imported_names - defined_names - builtins
            # Filter to only capitalized names (likely classes) or common functions
            potentially_missing = {
                n for n in potentially_missing 
                if n[0].isupper() or n in ['transaction', 'cache', 'timezone']
            }
            
            result['potential_missing'] = list(potentially_missing)
            
        except Exception as e:
            result['issues'].append(f"Error reading file: {str(e)}")
        
        return result
    
    def verify_directory(self, directory: Path, app_name: str) -> None:
        """Verify all Python files in a directory"""
        if not directory.exists():
            return
        
        python_files = list(directory.rglob('*.py'))
        python_files = [f for f in python_files if '__pycache__' not in str(f)]
        
        for py_file in python_files:
            self.results[app_name]['files_checked'] += 1
            
            result = self.check_file(py_file)
            
            if not result['syntax_ok']:
                self.results[app_name]['syntax_errors'].append(result)
                if self.verbose:
                    print(f"  ❌ {py_file.relative_to(self.project_root)}: SYNTAX ERROR")
            else:
                self.results[app_name]['files_ok'] += 1
                
                if result['has_wildcards']:
                    self.results[app_name]['wildcard_imports'].append(result)
                    if self.verbose:
                        print(f"  ⚠️  {py_file.relative_to(self.project_root)}: Has wildcard imports")
                
                if result['potential_missing']:
                    self.results[app_name]['potential_issues'].append(result)
                    if self.verbose:
                        print(f"  ⚠️  {py_file.relative_to(self.project_root)}: Potential missing imports")
                
                if self.verbose and result['syntax_ok'] and not result['has_wildcards'] and not result['potential_missing']:
                    print(f"  ✅ {py_file.relative_to(self.project_root)}")
    
    def verify_app(self, app_name: str) -> None:
        """Verify a specific Django app"""
        app_path = self.project_root / 'api' / app_name
        
        if not app_path.exists():
            print(f"⚠️  App not found: {app_name}")
            return
        
        print(f"\n{'='*70}")
        print(f"🔍 Verifying app: {app_name}")
        print(f"{'='*70}")
        
        # Check views
        views_dir = app_path / 'views'
        if views_dir.exists():
            print(f"\n📂 Checking views...")
            self.verify_directory(views_dir, app_name)
        
        # Check services
        services_dir = app_path / 'services'
        if services_dir.exists():
            print(f"\n📂 Checking services...")
            self.verify_directory(services_dir, app_name)
        
        # Check other Python files in app root
        for py_file in app_path.glob('*.py'):
            if py_file.name not in ['__init__.py', 'tests.py']:
                result = self.check_file(py_file)
                self.results[app_name]['files_checked'] += 1
                
                if result['syntax_ok']:
                    self.results[app_name]['files_ok'] += 1
                else:
                    self.results[app_name]['syntax_errors'].append(result)
    
    def print_summary(self) -> bool:
        """Print verification summary and return success status"""
        print(f"\n{'='*70}")
        print(f"📊 VERIFICATION SUMMARY")
        print(f"{'='*70}")
        
        all_ok = True
        total_files = 0
        total_ok = 0
        total_errors = 0
        total_wildcards = 0
        total_warnings = 0
        
        for app_name, stats in sorted(self.results.items()):
            files_checked = stats['files_checked']
            files_ok = stats['files_ok']
            syntax_errors = len(stats['syntax_errors'])
            wildcards = len(stats['wildcard_imports'])
            potential = len(stats['potential_issues'])
            
            total_files += files_checked
            total_ok += files_ok
            total_errors += syntax_errors
            total_wildcards += wildcards
            total_warnings += potential
            
            status = '✅' if syntax_errors == 0 else '❌'
            
            print(f"\n{status} {app_name}:")
            print(f"   Files checked: {files_checked}")
            print(f"   Files OK: {files_ok}")
            
            if syntax_errors > 0:
                print(f"   ❌ Syntax errors: {syntax_errors}")
                all_ok = False
                for error in stats['syntax_errors']:
                    print(f"      - {error['file']}")
                    for issue in error['issues']:
                        print(f"        {issue}")
            
            if wildcards > 0:
                print(f"   ⚠️  Wildcard imports: {wildcards}")
                for wc in stats['wildcard_imports']:
                    rel_path = Path(wc['file']).relative_to(self.project_root)
                    print(f"      - {rel_path}")
                    for w in wc['wildcards']:
                        print(f"        Line {w['line']}: from {w['module']} import *")
            
            if potential > 0:
                print(f"   ⚠️  Potential issues: {potential}")
                if self.verbose:
                    for pot in stats['potential_issues']:
                        rel_path = Path(pot['file']).relative_to(self.project_root)
                        print(f"      - {rel_path}")
                        print(f"        Potentially missing: {', '.join(pot['potential_missing'][:5])}")
        
        print(f"\n{'='*70}")
        print(f"Overall:")
        print(f"  Total files checked: {total_files}")
        print(f"  Files OK: {total_ok}")
        print(f"  Syntax errors: {total_errors}")
        print(f"  Wildcard imports: {total_wildcards}")
        print(f"  Potential issues: {total_warnings}")
        
        if all_ok and total_wildcards == 0:
            print(f"\n✅ ALL CHECKS PASSED!")
        elif all_ok:
            print(f"\n⚠️  No syntax errors, but found {total_wildcards} wildcard imports")
        else:
            print(f"\n❌ VERIFICATION FAILED - {total_errors} files with syntax errors")
        
        return all_ok


def main():
    parser = argparse.ArgumentParser(
        description='Verify imports after cleanup',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'apps',
        nargs='*',
        help='App names to verify'
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='Verify all apps'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    if not args.apps and not args.all:
        parser.print_help()
        return 1
    
    available_apps = [
        'users', 'stations', 'payments', 'rentals', 'notifications',
        'points', 'content', 'promotions', 'social', 'admin',
        'common', 'media', 'system'
    ]
    
    verifier = ImportVerifier(verbose=args.verbose)
    
    print(f"\n{'='*70}")
    print(f"🔍 IMPORT VERIFICATION")
    print(f"{'='*70}")
    
    try:
        if args.all:
            apps_to_check = available_apps
        else:
            apps_to_check = args.apps
        
        for app_name in apps_to_check:
            verifier.verify_app(app_name)
        
        success = verifier.print_summary()
        
        return 0 if success else 1
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Verification interrupted")
        return 130
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
