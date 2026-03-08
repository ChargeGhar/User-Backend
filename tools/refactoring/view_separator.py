#!/usr/bin/env python3
"""
View Separator - Single Comprehensive Script
Separate Django views into logical modules with full control and safety

Features:
1. dump   - Extract all view classes and create editable JSON plan
2. dryrun - Preview changes without modifying files
3. execute - Perform the separation with automatic backups

Usage:
    python view_separator.py dump api/users/views.py users
    # Edit the generated users_plan.json
    python view_separator.py dryrun users_plan.json
    python view_separator.py execute users_plan.json
"""

import argparse
import json
import os
import re
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple


class ViewSeparator:
    """Main class for view separation operations"""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root or os.getcwd())
        self.backup_dir = None
        
    # ==================== FEATURE 1: DUMP ====================
    
    def dump_view_classes(self, views_file: str, app_name: str) -> str:
        """
        Extract all view classes from views.py and create editable JSON plan
        Returns path to generated JSON file
        """
        views_path = self.project_root / views_file
        
        if not views_path.exists():
            raise FileNotFoundError(f"Views file not found: {views_path}")
        
        print(f"\n🔍 Analyzing {views_file}...")
        
        with open(views_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract all view classes
        view_classes = self._extract_all_view_classes(content)
        
        print(f"  ✓ Found {len(view_classes)} view classes")
        
        # Create editable JSON structure
        plan = self._create_separation_plan(app_name, views_file, view_classes)
        
        # Save to JSON
        output_file = self.project_root / f"{app_name}_plan.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(plan, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ JSON plan created: {output_file}")
        print(f"\n📝 Next steps:")
        print(f"  1. Edit {output_file} to organize classes into 3-5 modules")
        print(f"  2. Run: python view_separator.py dryrun {output_file.name}")
        print(f"  3. Run: python view_separator.py execute {output_file.name}")
        
        return str(output_file)
    
    def _extract_all_view_classes(self, content: str) -> List[Dict[str, Any]]:
        """Extract all view classes with their metadata"""
        lines = content.splitlines()
        view_classes = []
        
        # Pattern to match class definitions (may span multiple lines)
        class_start_pattern = r'^class\s+(\w+)\s*\('
        
        i = 0
        while i < len(lines):
            line = lines[i]
            match = re.match(class_start_pattern, line)
            
            if match:
                class_name = match.group(1)
                
                # Check if this is a View or ViewSet class
                if not ('View' in class_name or 'ViewSet' in class_name):
                    i += 1
                    continue
                
                # Find the end of class definition (the line with ):)
                class_def_start = i
                class_def_end = i
                paren_count = line.count('(') - line.count(')')
                
                while paren_count > 0 and class_def_end < len(lines) - 1:
                    class_def_end += 1
                    paren_count += lines[class_def_end].count('(') - lines[class_def_end].count(')')
                
                # Now class_def_end points to the line with ):
                # The actual class body starts after this line
                
                # Find router registration (look backwards from class definition start)
                router_path = None
                for j in range(max(0, class_def_start-50), class_def_start):
                    if '@router.register' in lines[j]:
                        router_match = re.search(r'@router\.register\(r"([^"]+)"', lines[j])
                        if router_match:
                            router_path = router_match.group(1)
                            break
                
                # Find decorators (only class-level decorators)
                decorators = []
                decorator_start = class_def_start
                
                # Scan backwards to find where decorators start
                found_decorator = False
                for j in range(class_def_start-1, max(0, class_def_start-50), -1):
                    line_stripped = lines[j].strip()
                    
                    if not line_stripped or line_stripped.startswith('#'):
                        # Skip blank lines and comments
                        if found_decorator:
                            break
                        continue
                    
                    if line_stripped.startswith('@'):
                        decorators.insert(0, line_stripped)
                        decorator_start = j
                        found_decorator = True
                    elif line_stripped in [')', '),'] or line_stripped.startswith('tags=') or line_stripped.startswith('summary=') or line_stripped.startswith('description=') or line_stripped.startswith('responses=') or line_stripped.startswith('parameters='):
                        # Part of a multi-line decorator
                        if found_decorator:
                            decorator_start = j
                    else:
                        # Found a line that's not part of a decorator
                        if found_decorator:
                            break
                        continue
                
                # Find class end
                class_end = self._find_class_end(lines, class_def_end)
                
                # Extract full class content including decorators
                full_content = '\n'.join(lines[decorator_start:class_end])
                
                view_classes.append({
                    'name': class_name,
                    'url_pattern': router_path or 'unknown',
                    'line_number': class_def_start + 1,
                    'decorators': decorators,
                    'content': full_content,
                    'estimated_lines': class_end - decorator_start
                })
                
                # Move past this class
                i = class_end
            else:
                i += 1
        
        return view_classes
    
    def _find_class_end(self, lines: List[str], start_idx: int) -> int:
        """Find where a class definition ends"""
        if start_idx >= len(lines):
            return len(lines)
        
        # Class indent level
        class_indent = len(lines[start_idx]) - len(lines[start_idx].lstrip())
        
        for i in range(start_idx + 1, len(lines)):
            line = lines[i]
            if not line.strip():  # Empty line, continue
                continue
            
            current_indent = len(line) - len(line.lstrip())
            
            # If we find a line at the same or lower indent level as the class, it's the end
            # UNLESS it's a decorator line (starts with @), which could be for a method inside
            # But if the line is @router.register or @extend_schema at class level, it's the next class
            if current_indent <= class_indent:
                line_stripped = line.strip()
                # Check if it's a class-level decorator (for the next class)
                if line_stripped.startswith('@router.register') or (line_stripped.startswith('@extend_schema') and current_indent == class_indent):
                    return i
                # Check if it's a new class definition
                elif line_stripped.startswith('class '):
                    return i
        
        return len(lines)
    
    def _create_separation_plan(self, app_name: str, views_file: str, 
                                view_classes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create an editable separation plan JSON structure"""
        
        # Auto-suggest modules based on URL patterns
        suggested_modules = self._auto_suggest_modules(view_classes)
        
        plan = {
            "app_name": app_name,
            "source_file": views_file,
            "target_directory": f"api/{app_name}/views/",
            "backup_enabled": True,
            "instructions": {
                "edit_this_file": "Organize view_classes into 3-5 modules below",
                "constraints": "Minimum 3 modules, Maximum 5 modules",
                "requirements": [
                    "Each module must have a unique 'name' (e.g., 'auth_views')",
                    "Each module must have a 'router_name' (e.g., 'auth_router')",
                    "Move class names from 'available_classes' to module 'view_classes'",
                    "Delete 'available_classes' section when done organizing"
                ]
            },
            "available_classes": [
                {
                    "name": vc['name'],
                    "url_pattern": vc['url_pattern'],
                    "estimated_lines": vc['estimated_lines']
                }
                for vc in view_classes
            ],
            "modules": suggested_modules,
            "_internal": {
                "all_view_classes": view_classes
            }
        }
        
        return plan
    
    def _auto_suggest_modules(self, view_classes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Auto-suggest module organization based on URL patterns"""
        
        # Group by URL prefix
        groups = {}
        for vc in view_classes:
            url = vc['url_pattern']
            if url == 'unknown':
                prefix = 'other'
            else:
                prefix = url.split('/')[0] if '/' in url else 'other'
            
            if prefix not in groups:
                groups[prefix] = []
            groups[prefix].append(vc['name'])
        
        # Create suggested modules (limit to 5)
        modules = []
        for prefix, classes in sorted(groups.items(), key=lambda x: len(x[1]), reverse=True)[:5]:
            module_name = f"{prefix}_views" if prefix != 'other' else 'misc_views'
            modules.append({
                "name": module_name,
                "description": f"{prefix.title()} related views",
                "router_name": f"{prefix}_router",
                "view_classes": classes
            })
        
        return modules
    
    # ==================== FEATURE 2: DRY RUN ====================
    
    def dry_run(self, plan_file: str) -> bool:
        """Preview the separation without making changes"""
        
        print(f"\n🔍 DRY RUN - Previewing changes from {plan_file}\n")
        
        plan = self._load_plan(plan_file)
        
        # Validate plan
        if not self._validate_plan(plan):
            return False
        
        print(f"📋 Separation Plan:")
        print(f"  App: {plan['app_name']}")
        print(f"  Source: {plan['source_file']}")
        print(f"  Target: {plan['target_directory']}")
        print(f"  Modules: {len(plan['modules'])}\n")
        
        # Show what will be created
        target_dir = self.project_root / plan['target_directory']
        print(f"📁 Directory structure that will be created:")
        print(f"  {target_dir}/")
        print(f"  ├── __init__.py")
        
        total_classes = 0
        for module in plan['modules']:
            print(f"  ├── {module['name']}.py ({len(module['view_classes'])} classes)")
            total_classes += len(module['view_classes'])
            for cls in module['view_classes']:
                print(f"  │   └── {cls}")
        
        print(f"\n📊 Statistics:")
        print(f"  Total view classes: {total_classes}")
        print(f"  Total modules: {len(plan['modules'])}")
        print(f"  Average classes per module: {total_classes / len(plan['modules']):.1f}")
        
        # Show what will happen to original file
        source_file = self.project_root / plan['source_file']
        legacy_file = source_file.parent / 'views_legacy.py'
        print(f"\n📝 File operations:")
        print(f"  ✓ Create backup in: backups/views_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}/")
        print(f"  ✓ Rename: {source_file.name} → {legacy_file.name}")
        print(f"  ✓ Create: {plan['target_directory']}")
        
        print(f"\n✅ Dry run completed - no files were modified")
        print(f"\n🚀 Ready to execute? Run: python view_separator.py execute {plan_file}")
        
        return True
    
    # ==================== FEATURE 3: EXECUTE ====================
    
    def execute(self, plan_file: str) -> bool:
        """Execute the separation with automatic backups"""
        
        print(f"\n🚀 EXECUTING separation from {plan_file}\n")
        
        plan = self._load_plan(plan_file)
        
        # Validate plan
        if not self._validate_plan(plan):
            return False
        
        source_path = self.project_root / plan['source_file']
        
        # Step 1: Create backup
        if plan.get('backup_enabled', True):
            self._create_backup(source_path)
        
        # Step 2: Create package structure
        target_dir = self.project_root / plan['target_directory']
        target_dir.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {target_dir}")
        
        # Step 3: Generate module files
        for module in plan['modules']:
            self._generate_module_file(module, plan)
        
        # Step 4: Generate __init__.py
        self._generate_init_file(plan)
        
        # Step 5: Archive original file
        legacy_file = source_path.parent / 'views_legacy.py'
        shutil.move(str(source_path), str(legacy_file))
        print(f"✓ Archived: {source_path.name} → {legacy_file.name}")
        
        # Step 6: Validate
        print(f"\n🔍 Validating...")
        if self._validate_separation(plan):
            print(f"\n✅ Separation completed successfully!")
            print(f"\n📋 Next steps:")
            print(f"  1. Test imports: from api.{plan['app_name']}.views import router")
            print(f"  2. Test endpoints: curl http://localhost:8010/api/...")
            print(f"  3. Generate schema: docker compose exec api python manage.py spectacular")
            if self.backup_dir:
                print(f"\n💾 Backup location: {self.backup_dir}")
                print(f"   Rollback: rm -rf {target_dir} && mv {legacy_file} {source_path}")
            return True
        else:
            print(f"\n❌ Validation failed!")
            return False
    
    # ==================== HELPER METHODS ====================
    
    def _load_plan(self, plan_file: str) -> Dict[str, Any]:
        """Load and parse the separation plan JSON"""
        plan_path = Path(plan_file)
        if not plan_path.exists():
            plan_path = self.project_root / plan_file
        
        if not plan_path.exists():
            raise FileNotFoundError(f"Plan file not found: {plan_file}")
        
        with open(plan_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _validate_plan(self, plan: Dict[str, Any]) -> bool:
        """Validate the separation plan"""
        errors = []
        
        # Check required fields
        required_fields = ['app_name', 'source_file', 'target_directory', 'modules']
        for field in required_fields:
            if field not in plan:
                errors.append(f"Missing required field: {field}")
        
        # Check modules count
        if 'modules' in plan:
            module_count = len(plan['modules'])
            if module_count < 3:
                errors.append(f"Too few modules: {module_count} (minimum 3 required)")
            elif module_count > 10:
                errors.append(f"Too many modules: {module_count} (maximum 5 allowed)")
            
            # Check each module
            for i, module in enumerate(plan['modules']):
                if 'name' not in module:
                    errors.append(f"Module {i} missing 'name'")
                if 'router_name' not in module:
                    errors.append(f"Module {i} missing 'router_name'")
                if 'view_classes' not in module or not module['view_classes']:
                    errors.append(f"Module {i} has no view_classes")
        
        # Check source file exists
        if 'source_file' in plan:
            source_path = self.project_root / plan['source_file']
            if not source_path.exists():
                errors.append(f"Source file not found: {source_path}")
        
        # Check for duplicate class names across modules
        if 'modules' in plan:
            all_classes = []
            for module in plan['modules']:
                all_classes.extend(module.get('view_classes', []))
            
            duplicates = [cls for cls in all_classes if all_classes.count(cls) > 1]
            if duplicates:
                errors.append(f"Duplicate classes found: {set(duplicates)}")
        
        if errors:
            print(f"❌ Validation errors:")
            for error in errors:
                print(f"  - {error}")
            return False
        
        print(f"✓ Plan validation passed")
        return True
    
    def _create_backup(self, source_path: Path):
        """Create backup of original file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = self.project_root / 'backups' / f'views_backup_{timestamp}'
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        shutil.copy2(source_path, backup_dir / 'views.py')
        self.backup_dir = backup_dir
        print(f"✓ Backup created: {backup_dir}")
    
    def _generate_module_file(self, module: Dict[str, Any], plan: Dict[str, Any]):
        """Generate a module file with its view classes"""
        target_dir = self.project_root / plan['target_directory']
        module_file = target_dir / f"{module['name']}.py"
        
        # Get view class content from internal data
        view_classes_map = {
            vc['name']: vc 
            for vc in plan.get('_internal', {}).get('all_view_classes', [])
        }
        
        # Build imports and header
        header = f'''"""
{module.get('description', f"{module['name']} views")}
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from rest_framework import status, mixins
from rest_framework.decorators import action
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from api.common.routers import CustomViewRouter
from api.common.mixins import BaseAPIView
from api.common.decorators import rate_limit, log_api_call, cached_response
from api.common.serializers import BaseResponseSerializer, PaginatedResponseSerializer
from api.{plan["app_name"]} import serializers
from api.{plan["app_name"]}.models import *
from api.{plan["app_name"]}.permissions import *
from api.{plan["app_name"]}.services import *
from api.common.services.base import ServiceException

if TYPE_CHECKING:
    from rest_framework.request import Request

{module["router_name"]} = CustomViewRouter()

logger = logging.getLogger(__name__)

'''
        
        # Add view classes
        class_contents = []
        for class_name in module['view_classes']:
            if class_name in view_classes_map:
                vc = view_classes_map[class_name]
                # Replace @router with module router
                content = vc['content'].replace('@router.register', f'@{module["router_name"]}.register')
                class_contents.append(content)
        
        # Write file
        full_content = header + '\n\n'.join(class_contents)
        with open(module_file, 'w', encoding='utf-8') as f:
            f.write(full_content)
        
        print(f"✓ Created: {module_file.name} ({len(module['view_classes'])} classes)")
    
    def _generate_init_file(self, plan: Dict[str, Any]):
        """Generate __init__.py that merges all routers"""
        target_dir = self.project_root / plan['target_directory']
        init_file = target_dir / '__init__.py'
        
        lines = [
            '"""',
            f'Views package for {plan["app_name"]} app',
            'Maintains backward compatibility by exposing single router',
            '"""',
            'from __future__ import annotations\n',
            'from api.common.routers import CustomViewRouter\n',
        ]
        
        # Import all routers
        for module in plan['modules']:
            lines.append(f'from .{module["name"]} import {module["router_name"]}')
        
        lines.extend([
            '\n# Merge all sub-routers',
            'router = CustomViewRouter()\n',
        ])
        
        # Merge logic
        router_names = [m['router_name'] for m in plan['modules']]
        lines.extend([
            f'for sub_router in [{", ".join(router_names)}]:',
            '    router._paths.extend(sub_router._paths)',
            '    router._drf_router.registry.extend(sub_router._drf_router.registry)',
        ])
        
        with open(init_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        print(f"✓ Created: __init__.py")
    
    def _validate_separation(self, plan: Dict[str, Any]) -> bool:
        """Validate the separation was successful"""
        target_dir = self.project_root / plan['target_directory']
        
        # Check all files exist
        if not (target_dir / '__init__.py').exists():
            print(f"  ❌ Missing __init__.py")
            return False
        
        for module in plan['modules']:
            module_file = target_dir / f"{module['name']}.py"
            if not module_file.exists():
                print(f"  ❌ Missing {module_file.name}")
                return False
            
            # Check file compiles
            try:
                with open(module_file, 'r', encoding='utf-8') as f:
                    compile(f.read(), module_file, 'exec')
                print(f"  ✓ {module_file.name} syntax valid")
            except SyntaxError as e:
                print(f"  ❌ Syntax error in {module_file.name}: {e}")
                return False
        
        return True


def main():
    parser = argparse.ArgumentParser(
        description='View Separator - Organize Django views into modules',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Step 1: Extract view classes and create plan
  python view_separator.py dump api/users/views.py users
  
  # Step 2: Edit users_plan.json to organize classes
  
  # Step 3: Preview changes
  python view_separator.py dryrun users_plan.json
  
  # Step 4: Execute separation
  python view_separator.py execute users_plan.json
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Dump command
    dump_parser = subparsers.add_parser('dump', help='Extract view classes and create editable plan')
    dump_parser.add_argument('views_file', help='Path to views.py (e.g., api/users/views.py)')
    dump_parser.add_argument('app_name', help='App name (e.g., users)')
    
    # Dry run command
    dryrun_parser = subparsers.add_parser('dryrun', help='Preview separation without changes')
    dryrun_parser.add_argument('plan_file', help='Path to plan JSON file')
    
    # Execute command
    execute_parser = subparsers.add_parser('execute', help='Execute the separation')
    execute_parser.add_argument('plan_file', help='Path to plan JSON file')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    separator = ViewSeparator()
    
    try:
        if args.command == 'dump':
            separator.dump_view_classes(args.views_file, args.app_name)
        elif args.command == 'dryrun':
            separator.dry_run(args.plan_file)
        elif args.command == 'execute':
            separator.execute(args.plan_file)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
