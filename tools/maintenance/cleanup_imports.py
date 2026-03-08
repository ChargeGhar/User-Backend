#!/usr/bin/env python3
"""
Import Cleanup Script - Using autoflake
========================================

This script uses autoflake to clean up imports in views, services, and serializers directories.

Features:
- Removes unused imports (including third-party)
- Expands wildcard imports (from X import *)
- Removes unused variables
- Removes duplicate keys
- Safe backup before changes
- Comprehensive reporting

Usage:
    # Clean specific app
    python tools/cleanup_imports.py users
    
    # Clean multiple apps
    python tools/cleanup_imports.py users stations payments
    
    # Clean all apps
    python tools/cleanup_imports.py --all
    
    # Preview mode (no changes)
    python tools/cleanup_imports.py users --preview
    
    # Verbose output
    python tools/cleanup_imports.py users --verbose
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import shutil


class ImportCleanup:
    """Cleanup imports using autoflake"""
    
    def __init__(self, project_root: str = None, preview: bool = False, verbose: bool = False):
        self.project_root = Path(project_root or os.getcwd())
        self.preview = preview
        self.verbose = verbose
        self.backup_dir = None
        
        # Available Django apps
        self.available_apps = [
            'users', 'stations', 'payments', 'rentals', 'notifications',
            'points', 'content', 'promotions', 'social', 'admin',
            'common', 'media', 'system'
        ]
    
    def create_backup(self):
        """Create timestamped backup directory"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.backup_dir = self.project_root / 'backups' / f'autoflake_{timestamp}'
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        print(f"📦 Backup directory: {self.backup_dir}")
    
    def backup_directory(self, directory: Path):
        """Backup a directory before modification"""
        if not self.backup_dir:
            self.create_backup()
        
        try:
            rel_path = directory.relative_to(self.project_root)
            backup_path = self.backup_dir / rel_path
            
            if directory.exists():
                shutil.copytree(directory, backup_path, dirs_exist_ok=True)
                if self.verbose:
                    print(f"  💾 Backed up: {rel_path}")
        except Exception as e:
            print(f"  ⚠️  Backup warning: {e}")
    
    def run_autoflake(self, directory: Path) -> dict:
        """Run autoflake on a directory"""
        if not directory.exists():
            return {'error': f'Directory not found: {directory}'}
        
        # Build autoflake command
        cmd = [
            'autoflake',
            '--recursive',
            '--remove-all-unused-imports',  # Remove ALL unused imports (not just stdlib)
            '--expand-star-imports',  # Expand wildcard imports
            '--remove-unused-variables',  # Remove unused variables
            '--remove-duplicate-keys',  # Remove duplicate dict keys
            '--ignore-init-module-imports',  # Keep __init__.py imports
        ]
        
        if not self.preview:
            cmd.append('--in-place')  # Modify files
        
        if self.verbose:
            cmd.append('--verbose')
        
        cmd.append(str(directory))
        
        # Run autoflake
        try:
            if self.preview:
                print(f"  👁️  Preview mode - showing changes:")
                result = subprocess.run(cmd, capture_output=True, text=True, check=False)
                if result.stdout:
                    print(result.stdout)
                if result.returncode != 0 and result.stderr:
                    print(f"  ⚠️  Warnings: {result.stderr}")
            else:
                result = subprocess.run(cmd, capture_output=True, text=True, check=False)
                if self.verbose and result.stdout:
                    print(result.stdout)
                if result.returncode != 0 and result.stderr:
                    print(f"  ⚠️  Warnings: {result.stderr}")
            
            return {
                'success': True,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
        except Exception as e:
            return {'error': str(e)}
    
    def cleanup_app(self, app_name: str) -> dict:
        """Clean up imports for a specific app"""
        if app_name not in self.available_apps:
            print(f"⚠️  Unknown app: {app_name}")
            return {'error': f'Unknown app: {app_name}'}
        
        app_path = self.project_root / 'api' / app_name
        
        if not app_path.exists():
            print(f"⚠️  App directory not found: {app_path}")
            return {'error': f'App not found: {app_name}'}
        
        print(f"\n{'='*70}")
        print(f"🧹 Cleaning app: {app_name}")
        print(f"{'='*70}")
        
        results = {'app': app_name, 'views': None, 'services': None, 'serializers': None}
        
        # Process views directory
        views_dir = app_path / 'views'
        if views_dir.exists() and views_dir.is_dir():
            print(f"\n📂 Processing views...")
            
            if not self.preview:
                self.backup_directory(views_dir)
            
            result = self.run_autoflake(views_dir)
            results['views'] = result
            
            if 'error' not in result:
                print(f"  ✅ Views cleaned")
            else:
                print(f"  ❌ Error: {result['error']}")
        else:
            print(f"  ℹ️  No views directory")
        
        # Process services directory
        services_dir = app_path / 'services'
        if services_dir.exists() and services_dir.is_dir():
            print(f"\n📂 Processing services...")
            
            if not self.preview:
                self.backup_directory(services_dir)
            
            result = self.run_autoflake(services_dir)
            results['services'] = result
            
            if 'error' not in result:
                print(f"  ✅ Services cleaned")
            else:
                print(f"  ❌ Error: {result['error']}")
        else:
            print(f"  ℹ️  No services directory")
        
        # Process serializers directory
        serializers_dir = app_path / 'serializers'
        if serializers_dir.exists() and serializers_dir.is_dir():
            print(f"\n📂 Processing serializers...")
            
            if not self.preview:
                self.backup_directory(serializers_dir)
            
            result = self.run_autoflake(serializers_dir)
            results['serializers'] = result
            
            if 'error' not in result:
                print(f"  ✅ Serializers cleaned")
            else:
                print(f"  ❌ Error: {result['error']}")
        else:
            print(f"  ℹ️  No serializers directory")
        
        return results
    
    def cleanup_all_apps(self) -> dict:
        """Clean up all available apps"""
        print(f"\n{'='*70}")
        print(f"🧹 CLEANING ALL APPS")
        print(f"{'='*70}")
        
        all_results = {}
        
        for app_name in self.available_apps:
            result = self.cleanup_app(app_name)
            all_results[app_name] = result
        
        return all_results
    
    def print_summary(self, results: dict):
        """Print summary of cleanup operations"""
        print(f"\n{'='*70}")
        print(f"📊 CLEANUP SUMMARY")
        print(f"{'='*70}")
        
        total_apps = len(results)
        successful_apps = sum(1 for r in results.values() if 'error' not in r)
        
        print(f"  Total apps processed: {total_apps}")
        print(f"  Successful: {successful_apps}")
        print(f"  Failed: {total_apps - successful_apps}")
        
        if self.preview:
            print(f"\n  👁️  PREVIEW MODE - No files were modified")
        elif self.backup_dir:
            print(f"\n  💾 Backup saved to: {self.backup_dir.relative_to(self.project_root)}")
        
        print(f"\n  ✅ Done!")


def main():
    parser = argparse.ArgumentParser(
        description='Clean up imports in Django apps using autoflake',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Clean single app
  python tools/cleanup_imports.py users
  
  # Clean multiple apps
  python tools/cleanup_imports.py users stations payments
  
  # Clean all apps
  python tools/cleanup_imports.py --all
  
  # Preview mode (no changes)
  python tools/cleanup_imports.py users --preview
  
  # Verbose output
  python tools/cleanup_imports.py users --verbose
  
What it does:
  - Removes ALL unused imports (including third-party)
  - Expands wildcard imports (from X import *)
  - Removes unused variables
  - Removes duplicate keys in dicts
  - Keeps __init__.py imports (safe)
  - Creates automatic backups (unless --preview)
  - Processes views, services, and serializers directories

Available apps:
  users, stations, payments, rentals, notifications, points,
  content, promotions, social, admin, common, media, system
        """
    )
    
    parser.add_argument(
        'apps',
        nargs='*',
        help='App names to clean (e.g., users stations payments)'
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='Clean all available apps'
    )
    
    parser.add_argument(
        '--preview',
        action='store_true',
        help='Preview changes without modifying files'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.apps and not args.all:
        parser.print_help()
        print("\n❌ Error: Specify app names or use --all")
        return 1
    
    # Initialize cleanup
    cleanup = ImportCleanup(preview=args.preview, verbose=args.verbose)
    
    print(f"\n{'='*70}")
    print(f"🧹 IMPORT CLEANUP USING AUTOFLAKE")
    print(f"{'='*70}")
    print(f"  Tool: autoflake 2.3.1")
    print(f"  Mode: {'PREVIEW' if args.preview else 'CLEANUP'}")
    print(f"  Project: {cleanup.project_root}")
    
    # Run cleanup
    try:
        if args.all:
            results = cleanup.cleanup_all_apps()
        else:
            results = {}
            for app_name in args.apps:
                result = cleanup.cleanup_app(app_name)
                results[app_name] = result
        
        # Print summary
        cleanup.print_summary(results)
        
        return 0
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Cleanup interrupted by user")
        return 130
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())