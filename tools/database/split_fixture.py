#!/usr/bin/env python3
"""
Django Fixture Splitter Tool

This tool splits Django fixture files by model type, allowing you to:
1. List all fixtures in an app
2. Split a specific fixture file by model types into separate files
3. Generate separate fixture files for each model in the same directory
4. Automatically delete the original fixture after successful split

Usage:
    python split_fixture.py --app <app_name> --list
    python split_fixture.py --app <app_name> --fixture <fixture_name>

Examples:
    python split_fixture.py --app notifications --list
    python split_fixture.py --app notifications --fixture notifications.json
    python split_fixture.py --app stations --fixture stations.json

Note: Split files are created in the same directory as the original fixture,
      and the original fixture is deleted after successful splitting.
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any, Optional


class FixtureSplitter:
    """Django fixture splitter utility"""
    
    def __init__(self, app_name: str, project_root: Optional[str] = None):
        self.app_name = app_name
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.app_path = self.project_root / "api" / app_name
        self.fixtures_path = self.app_path / "fixtures"
        
    def validate_app(self) -> bool:
        """Validate that the app exists"""
        if not self.app_path.exists():
            print(f"❌ App '{self.app_name}' not found at {self.app_path}")
            return False
            
        if not self.fixtures_path.exists():
            print(f"❌ Fixtures directory not found at {self.fixtures_path}")
            return False
            
        return True
    
    def list_fixtures(self) -> List[str]:
        """List all fixture files in the app"""
        if not self.validate_app():
            return []
            
        fixtures = []
        for file_path in self.fixtures_path.glob("*.json"):
            fixtures.append(file_path.name)
            
        return sorted(fixtures)
    
    def print_fixtures_list(self) -> None:
        """Print formatted list of fixtures"""
        fixtures = self.list_fixtures()
        
        if not fixtures:
            print(f"📂 No fixtures found in {self.fixtures_path}")
            return
            
        print(f"📂 Fixtures in '{self.app_name}' app:")
        print("=" * 50)
        
        for i, fixture in enumerate(fixtures, 1):
            fixture_path = self.fixtures_path / fixture
            try:
                with open(fixture_path, 'r') as f:
                    data = json.load(f)
                    
                # Count models
                model_counts = defaultdict(int)
                for item in data:
                    if isinstance(item, dict) and 'model' in item:
                        model_counts[item['model']] += 1
                
                print(f"{i:2d}. {fixture}")
                print(f"    📊 Total entries: {len(data)}")
                print(f"    🏗️  Models ({len(model_counts)}):")
                
                for model, count in sorted(model_counts.items()):
                    print(f"       - {model}: {count} entries")
                print()
                
            except Exception as e:
                print(f"{i:2d}. {fixture}")
                print(f"    ❌ Error reading file: {e}")
                print()
    
    def load_fixture(self, fixture_name: str) -> Optional[List[Dict[str, Any]]]:
        """Load fixture data from file"""
        fixture_path = self.fixtures_path / fixture_name
        
        if not fixture_path.exists():
            print(f"❌ Fixture '{fixture_name}' not found at {fixture_path}")
            return None
            
        try:
            with open(fixture_path, 'r') as f:
                data = json.load(f)
                
            if not isinstance(data, list):
                print(f"❌ Fixture '{fixture_name}' is not a valid Django fixture (should be a list)")
                return None
                
            return data
            
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in '{fixture_name}': {e}")
            return None
        except Exception as e:
            print(f"❌ Error loading '{fixture_name}': {e}")
            return None
    
    def split_fixture_by_models(self, fixture_name: str) -> bool:
        """Split fixture file by model types"""
        print(f"🔄 Splitting fixture: {fixture_name}")
        print("=" * 50)
        
        # Load fixture data
        data = self.load_fixture(fixture_name)
        if data is None:
            return False
            
        # Store original fixture path for deletion later
        original_fixture_path = self.fixtures_path / fixture_name
        
        # Group by model
        models_data = defaultdict(list)
        invalid_entries = []
        
        for item in data:
            if not isinstance(item, dict):
                invalid_entries.append(item)
                continue
                
            if 'model' not in item:
                invalid_entries.append(item)
                continue
                
            model_name = item['model']
            models_data[model_name].append(item)
        
        if invalid_entries:
            print(f"⚠️  Found {len(invalid_entries)} invalid entries (will be skipped)")
        
        if not models_data:
            print("❌ No valid model entries found in fixture")
            return False
        
        # Always use the same directory as the original fixture
        output_path = self.fixtures_path
        
        print(f"📊 Found {len(models_data)} different models:")
        
        # Create separate files for each model
        created_files = []
        
        for model_name, entries in models_data.items():
            # Generate filename from model name
            # e.g., "notifications.notificationtemplate" -> "notification_templates.json"
            app_prefix, model_class = model_name.split('.', 1) if '.' in model_name else ('', model_name)
            
            # Convert CamelCase to snake_case and pluralize
            filename = self._model_to_filename(model_class)
            output_file = output_path / f"{filename}.json"
            
            # Avoid overwriting the original fixture if names conflict
            if output_file.name == fixture_name:
                # Add model prefix to avoid conflict
                filename = f"{app_prefix}_{filename}" if app_prefix else f"model_{filename}"
                output_file = output_path / f"{filename}.json"
            
            try:
                with open(output_file, 'w') as f:
                    json.dump(entries, f, indent=2, ensure_ascii=False)
                
                created_files.append(output_file.name)
                print(f"   ✅ {model_name}: {len(entries)} entries -> {output_file.name}")
                
            except Exception as e:
                print(f"   ❌ {model_name}: Error writing file - {e}")
                return False
        
        # Delete the original fixture file after successful split
        try:
            original_fixture_path.unlink()
            print(f"🗑️  Deleted original fixture: {fixture_name}")
        except Exception as e:
            print(f"⚠️  Could not delete original fixture '{fixture_name}': {e}")
            # Don't fail the operation if we can't delete the original
        
        print(f"\n🎉 Successfully split '{fixture_name}' into {len(created_files)} files")
        
        return True
    
    def _model_to_filename(self, model_class: str) -> str:
        """Convert model class name to filename"""
        # Convert CamelCase to snake_case
        import re
        
        # Insert underscore before uppercase letters (except first)
        snake_case = re.sub('([a-z0-9])([A-Z])', r'\1_\2', model_class).lower()
        
        # Simple pluralization rules
        if snake_case.endswith('y'):
            plural = snake_case[:-1] + 'ies'
        elif snake_case.endswith(('s', 'sh', 'ch', 'x', 'z')):
            plural = snake_case + 'es'
        elif snake_case.endswith('f'):
            plural = snake_case[:-1] + 'ves'
        elif snake_case.endswith('fe'):
            plural = snake_case[:-2] + 'ves'
        else:
            plural = snake_case + 's'
            
        return plural


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(
        description="Django Fixture Splitter Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  List fixtures in notifications app:
    python split_fixture.py --app notifications --list
    
  Split notifications fixture (creates files in same directory, deletes original):
    python split_fixture.py --app notifications --fixture notifications.json
    
  Split stations fixture:
    python split_fixture.py --app stations --fixture stations.json
        """
    )
    
    parser.add_argument(
        '--app', 
        required=True,
        help='Django app name (e.g., notifications, stations, users)'
    )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all fixtures in the app'
    )
    
    parser.add_argument(
        '--fixture',
        help='Fixture file name to split (e.g., notifications.json)'
    )
    
    parser.add_argument(
        '--project-root',
        help='Project root directory (default: current directory)'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.list and not args.fixture:
        print("❌ Error: Either --list or --fixture must be specified")
        parser.print_help()
        sys.exit(1)
    
    if args.list and args.fixture:
        print("❌ Error: Cannot use --list and --fixture together")
        parser.print_help()
        sys.exit(1)
    
    # Initialize splitter
    splitter = FixtureSplitter(args.app, args.project_root)
    
    try:
        if args.list:
            # List fixtures
            print(f"🔍 Listing fixtures for app: {args.app}")
            print()
            splitter.print_fixtures_list()
            
        elif args.fixture:
            # Split fixture
            if not splitter.validate_app():
                sys.exit(1)
                
            success = splitter.split_fixture_by_models(args.fixture)
            if not success:
                sys.exit(1)
                
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()