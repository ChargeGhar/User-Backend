#!/usr/bin/env python3
"""
Service Separator - Single Comprehensive Script
Separate Django services into logical modules with full control and safety

Features:
1. dump   - Extract all service classes and create editable JSON plan
2. dryrun - Preview changes without modifying files
3. execute - Perform the separation with automatic backups

Usage:
    python service_separator.py dump api/users/services.py users
    # Edit the generated users_services_plan.json
    python service_separator.py dryrun users_services_plan.json
    python service_separator.py execute users_services_plan.json

Example:
    # Split points services
    python service_separator.py dump api/points/services.py points
    # Edit points_services_plan.json to organize into:
    #   - earning_services.py (PointsService, PointsEarningService)
    #   - redemption_services.py (PointsRedemptionService)
    #   - analytics_services.py (PointsAnalyticsService)
    python service_separator.py dryrun points_services_plan.json
    python service_separator.py execute points_services_plan.json
"""

import argparse
import json
import os
import re
import shutil
import ast
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple, Set


class ServiceSeparator:
    """Main class for service separation operations"""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root or os.getcwd())
        self.backup_dir = None
        
    # ==================== FEATURE 1: DUMP ====================
    
    def dump_service_classes(self, services_file: str, app_name: str) -> str:
        """
        Extract all service classes from services.py and create editable JSON plan
        Returns path to generated JSON file
        """
        services_path = self.project_root / services_file
        
        if not services_path.exists():
            raise FileNotFoundError(f"Services file not found: {services_path}")
        
        print(f"\n🔍 Analyzing {services_file}...")
        
        with open(services_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract all service classes with AST for accuracy
        file_imports, service_classes = self._extract_all_service_classes(content)
        
        print(f"  ✓ Found {len(service_classes)} service classes")
        print(f"  ✓ Extracted {len(file_imports.splitlines())} import statements")
        
        # Create editable JSON structure
        plan = self._create_separation_plan(app_name, services_file, file_imports, service_classes)
        
        # Save to JSON
        output_file = self.project_root / f"{app_name}_services_plan.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(plan, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ JSON plan created: {output_file}")
        print(f"\n📝 Next steps:")
        print(f"  1. Edit {output_file} to organize classes into 2-5 modules")
        print(f"  2. Run: python service_separator.py dryrun {output_file.name}")
        print(f"  3. Run: python service_separator.py execute {output_file.name}")
        
        return str(output_file)
    
    def _extract_all_service_classes(self, content: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Extract all service classes using AST for accuracy"""
        tree = ast.parse(content)
        lines = content.split('\n')
        
        # Extract module-level imports
        imports = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                # Get the exact source text for the import
                start_line = node.lineno - 1
                end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line + 1
                import_text = '\n'.join(lines[start_line:end_line])
                imports.append(import_text)
        
        file_imports = '\n'.join(imports)
        
        # Extract service classes
        service_classes = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name
                
                # Only include classes that look like services
                if not any(keyword in class_name.lower() for keyword in ['service', 'handler', 'manager', 'processor']):
                    continue
                
                # Get class definition lines (including decorators)
                start_line = node.lineno - 1
                end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line + 1
                
                # Look for decorators above the class
                decorator_start = start_line
                for i in range(start_line - 1, max(0, start_line - 20), -1):
                    line = lines[i].strip()
                    if line.startswith('@'):
                        decorator_start = i
                    elif line and not line.startswith('#'):
                        break
                
                # Extract full class content including decorators
                full_content = '\n'.join(lines[decorator_start:end_line])
                
                # Determine base class
                base_classes = []
                if node.bases:
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            base_classes.append(base.id)
                        elif isinstance(base, ast.Attribute):
                            base_classes.append(f"{base.value.id}.{base.attr}")
                
                # Extract docstring
                docstring = ast.get_docstring(node) or f"Service class for {class_name}"
                
                # Extract method names for context
                methods = [m.name for m in node.body if isinstance(m, ast.FunctionDef)]
                
                # Analyze imports needed by this class
                class_imports = self._extract_class_specific_imports(full_content, content)
                
                service_classes.append({
                    'name': class_name,
                    'base_classes': base_classes,
                    'line_number': start_line + 1,
                    'content': full_content,
                    'docstring': docstring,
                    'methods': methods,
                    'method_count': len(methods),
                    'estimated_lines': end_line - decorator_start,
                    'imports': list(class_imports)
                })
        
        return file_imports, service_classes
    
    def _extract_class_specific_imports(self, class_code: str, full_content: str) -> Set[str]:
        """Extract imports that are specifically needed by this class"""
        imports = set()
        
        # Find lazy imports inside the class (e.g., TYPE_CHECKING imports)
        lazy_import_pattern = r'from ([\w.]+) import ([\w, ]+)'
        matches = re.findall(lazy_import_pattern, class_code)
        
        for module, names in matches:
            # Skip if it's already in the file-level imports
            if module not in full_content.split('class ')[0]:
                imports.add(f"from {module} import {names}")
        
        return imports
    
    def _create_separation_plan(self, app_name: str, services_file: str, 
                                file_imports: str, service_classes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create an editable separation plan JSON structure"""
        
        # Auto-suggest modules based on class names and patterns
        suggested_modules = self._auto_suggest_modules(service_classes)
        
        plan = {
            "app_name": app_name,
            "source_file": services_file,
            "target_directory": f"api/{app_name}/services/",
            "backup_enabled": True,
            "instructions": {
                "info": "ONE CLASS PER FILE - Each service class gets its own module file",
                "auto_generated": "Modules are automatically created with snake_case filenames",
                "naming_convention": "CamelCase class names → snake_case filenames (e.g., AuthService → auth_service.py)",
                "customization": "You can edit module names and descriptions if needed",
                "structure": "Each module has exactly one service class for clarity and maintainability"
            },
            "available_classes": [
                {
                    "name": sc['name'],
                    "base_classes": sc['base_classes'],
                    "method_count": sc['method_count'],
                    "estimated_lines": sc['estimated_lines'],
                    "docstring": sc['docstring']
                }
                for sc in service_classes
            ],
            "modules": suggested_modules,
            "_internal": {
                "file_imports": file_imports,
                "all_service_classes": service_classes
            }
        }
        
        return plan
    
    def _auto_suggest_modules(self, service_classes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Auto-suggest module organization - ONE CLASS PER FILE"""
        
        # Create one module per service class
        modules = []
        
        for sc in service_classes:
            class_name = sc['name']
            
            # Convert CamelCase to snake_case for filename
            filename = self._camel_to_snake(class_name)
            
            # Generate description from class docstring or name
            description = sc.get('docstring', f"Service for {class_name}")
            if description == f"Service class for {class_name}":
                description = f"Service for {class_name}"
            
            modules.append({
                "name": filename,
                "description": description,
                "service_classes": [class_name]
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
            print(f"  ├── {module['name']}.py ({len(module['service_classes'])} classes)")
            total_classes += len(module['service_classes'])
            for cls in module['service_classes']:
                print(f"  │   └── {cls}")
        
        print(f"\n📊 Statistics:")
        print(f"  Total service classes: {total_classes}")
        print(f"  Total modules: {len(plan['modules'])}")
        print(f"  Average classes per module: {total_classes / len(plan['modules']):.1f}")
        
        # Show what will happen to original file
        source_file = self.project_root / plan['source_file']
        legacy_file = source_file.parent / 'services_legacy.py'
        print(f"\n📝 File operations:")
        print(f"  ✓ Create backup in: backups/services_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}/")
        print(f"  ✓ Rename: {source_file.name} → {legacy_file.name}")
        print(f"  ✓ Create: {plan['target_directory']}")
        
        # Show import examples
        print(f"\n📦 Import examples after separation:")
        print(f"  # Old import:")
        print(f"  from api.{plan['app_name']}.services import SomeService")
        print(f"  ")
        print(f"  # New import (still works via __init__.py):")
        print(f"  from api.{plan['app_name']}.services import SomeService")
        print(f"  ")
        print(f"  # Or import specific module:")
        print(f"  from api.{plan['app_name']}.services.{plan['modules'][0]['name']} import SomeService")
        
        print(f"\n✅ Dry run completed - no files were modified")
        print(f"\n🚀 Ready to execute? Run: python service_separator.py execute {plan_file}")
        
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
        legacy_file = source_path.parent / 'services_legacy.py'
        shutil.move(str(source_path), str(legacy_file))
        print(f"✓ Archived: {source_path.name} → {legacy_file.name}")
        
        # Step 6: Validate
        print(f"\n🔍 Validating...")
        if self._validate_separation(plan):
            print(f"\n✅ Separation completed successfully!")
            print(f"\n📋 Next steps:")
            print(f"  1. Test imports: from api.{plan['app_name']}.services import *")
            print(f"  2. Run tests: docker-compose exec api python manage.py test api.{plan['app_name']}")
            print(f"  3. Check for import errors: python manage.py check")
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
        
        # Check modules exist
        if 'modules' in plan:
            module_count = len(plan['modules'])
            if module_count < 1:
                errors.append(f"No modules defined")
            
            # Check each module
            for i, module in enumerate(plan['modules']):
                if 'name' not in module:
                    errors.append(f"Module {i} missing 'name'")
                if 'description' not in module:
                    errors.append(f"Module {i} missing 'description'")
                if 'service_classes' not in module or not module['service_classes']:
                    errors.append(f"Module {i} has no service_classes")
        
        # Check source file exists
        if 'source_file' in plan:
            source_path = self.project_root / plan['source_file']
            if not source_path.exists():
                errors.append(f"Source file not found: {source_path}")
        
        # Check for duplicate class names across modules
        if 'modules' in plan:
            all_classes = []
            for module in plan['modules']:
                all_classes.extend(module.get('service_classes', []))
            
            duplicates = [cls for cls in all_classes if all_classes.count(cls) > 1]
            if duplicates:
                errors.append(f"Duplicate classes found: {set(duplicates)}")
        
        # Check that all classes are accounted for
        if 'modules' in plan and '_internal' in plan:
            all_available = [sc['name'] for sc in plan['_internal'].get('all_service_classes', [])]
            all_assigned = []
            for module in plan['modules']:
                all_assigned.extend(module.get('service_classes', []))
            
            missing = set(all_available) - set(all_assigned)
            if missing:
                errors.append(f"Classes not assigned to any module: {missing}")
        
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
        backup_dir = self.project_root / 'backups' / f'services_backup_{timestamp}'
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        shutil.copy2(source_path, backup_dir / 'services.py')
        self.backup_dir = backup_dir
        print(f"✓ Backup created: {backup_dir}")
    
    def _generate_module_file(self, module: Dict[str, Any], plan: Dict[str, Any]):
        """Generate a module file with its service classes"""
        target_dir = self.project_root / plan['target_directory']
        module_file = target_dir / f"{module['name']}.py"
        
        # Get service class content from internal data
        service_classes_map = {
            sc['name']: sc 
            for sc in plan.get('_internal', {}).get('all_service_classes', [])
        }
        
        # Build file header
        header = f'''"""
{module['description']}
{'=' * 60}

This module contains service classes for {module['description'].lower()}.

Auto-generated by Service Separator
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
from __future__ import annotations

'''
        
        # Add file-level imports
        file_imports = plan.get('_internal', {}).get('file_imports', '')
        header += file_imports + '\n\n'
        
        # Add any additional imports needed by the classes in this module
        additional_imports = set()
        for class_name in module['service_classes']:
            if class_name in service_classes_map:
                sc = service_classes_map[class_name]
                additional_imports.update(sc.get('imports', []))
        
        if additional_imports:
            header += '# Additional imports for this module\n'
            header += '\n'.join(sorted(additional_imports)) + '\n\n'
        
        # Add service classes
        class_contents = []
        for class_name in module['service_classes']:
            if class_name in service_classes_map:
                sc = service_classes_map[class_name]
                class_contents.append(sc['content'])
        
        # Write file
        full_content = header + '\n\n\n'.join(class_contents) + '\n'
        with open(module_file, 'w', encoding='utf-8') as f:
            f.write(full_content)
        
        print(f"✓ Created: {module_file.name} ({len(module['service_classes'])} classes)")
    
    def _generate_init_file(self, plan: Dict[str, Any]):
        """Generate __init__.py that exports all services"""
        target_dir = self.project_root / plan['target_directory']
        init_file = target_dir / '__init__.py'
        
        lines = [
            '"""',
            f'Services package for {plan["app_name"]} app',
            '=' * 60,
            '',
            'This package contains all service classes organized by functionality.',
            'Maintains backward compatibility by re-exporting all services.',
            '',
            'Auto-generated by Service Separator',
            f'Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            '"""',
            'from __future__ import annotations\n',
        ]
        
        # Import all services from each module
        all_classes = []
        for module in plan['modules']:
            module_classes = module['service_classes']
            all_classes.extend(module_classes)
            
            # Import each class
            for class_name in module_classes:
                lines.append(f'from .{module["name"]} import {class_name}')
        
        lines.extend([
            '\n',
            '# Backward compatibility - all services available at package level',
            '__all__ = [',
        ])
        
        # Add __all__ export
        for class_name in sorted(all_classes):
            lines.append(f'    "{class_name}",')
        
        lines.extend([
            ']',
            '',
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
    
    def _camel_to_snake(self, name: str) -> str:
        """Convert CamelCase to snake_case"""
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1)
        return s2.lower()


def main():
    parser = argparse.ArgumentParser(
        description='Service Separator - Organize Django services into modules',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Step 1: Extract service classes and create plan
  python service_separator.py dump api/points/services.py points
  
  # Step 2: Edit points_services_plan.json to organize classes
  
  # Step 3: Preview changes
  python service_separator.py dryrun points_services_plan.json
  
  # Step 4: Execute separation
  python service_separator.py execute points_services_plan.json

Organization pattern:
  - ONE CLASS PER FILE for maximum clarity and maintainability
  - Automatic snake_case naming (AuthService → auth_service.py)
  - Each file contains exactly one service class
  - Clean imports via __init__.py for backward compatibility
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Dump command
    dump_parser = subparsers.add_parser('dump', help='Extract service classes and create editable plan')
    dump_parser.add_argument('services_file', help='Path to services.py (e.g., api/points/services.py)')
    dump_parser.add_argument('app_name', help='App name (e.g., points)')
    
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
    
    separator = ServiceSeparator()
    
    try:
        if args.command == 'dump':
            separator.dump_service_classes(args.services_file, args.app_name)
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
