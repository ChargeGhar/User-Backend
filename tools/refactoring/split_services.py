#!/usr/bin/env python3
"""
🔧 Service Splitter - Automatic Service File Splitting Tool
============================================================

This script automatically splits a monolithic services.py file into separate
service files based on class names, and updates imports accordingly.

Usage:
    python split_services.py

Features:
    - Detects all service classes in services.py
    - Creates separate files for each service class
    - Generates __init__.py with proper exports
    - Preserves imports and documentation
    - Creates backup of original file
"""

import os
import re
import ast
from typing import List, Dict, Set, Tuple
from datetime import datetime


class ServiceSplitter:
    """Automatically split services.py into separate service files"""
    
    def __init__(self, services_file: str = 'services.py'):
        self.services_file = services_file
        self.services_dir = 'services'
        self.backup_dir = 'services_backup'
        
    def run(self):
        """Main execution flow"""
        print("🚀 Starting Service Splitter...")
        print("=" * 60)
        
        # Step 1: Read original services.py
        print("\n📖 Step 1: Reading services.py...")
        with open(self.services_file, 'r') as f:
            content = f.read()
        print(f"   ✅ Read {len(content)} characters")
        
        # Step 2: Create backup
        print("\n💾 Step 2: Creating backup...")
        self._create_backup(content)
        print(f"   ✅ Backup created in {self.backup_dir}/")
        
        # Step 3: Parse file structure
        print("\n🔍 Step 3: Parsing file structure...")
        file_imports, classes = self._parse_file(content)
        print(f"   ✅ Found {len(classes)} service classes:")
        for class_name in classes.keys():
            print(f"      - {class_name}")
        
        # Step 4: Create services directory
        print("\n📁 Step 4: Creating services directory...")
        os.makedirs(self.services_dir, exist_ok=True)
        print(f"   ✅ Directory created: {self.services_dir}/")
        
        # Step 5: Split into separate files
        print("\n✂️  Step 5: Splitting services into files...")
        self._split_services(file_imports, classes)
        
        # Step 6: Create __init__.py
        print("\n📝 Step 6: Creating __init__.py...")
        self._create_init_file(classes)
        
        # Step 7: Summary
        print("\n" + "=" * 60)
        print("✅ Service splitting completed successfully!")
        print("\n📊 Summary:")
        print(f"   - Original file: {self.services_file}")
        print(f"   - Services directory: {self.services_dir}/")
        print(f"   - Files created: {len(classes) + 1} (including __init__.py)")
        print(f"   - Backup location: {self.backup_dir}/")
        print("\n🎯 Next steps:")
        print("   1. Review generated files in services/")
        print("   2. Test imports: from api.points.services import PointsService")
        print("   3. Delete services.py if everything works")
        print("   4. Update any direct imports in other files")
        print("\n" + "=" * 60)
    
    def _create_backup(self, content: str):
        """Create backup of original services.py"""
        os.makedirs(self.backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f"{self.backup_dir}/services_{timestamp}.py"
        with open(backup_file, 'w') as f:
            f.write(content)
    
    def _parse_file(self, content: str) -> Tuple[str, Dict[str, Dict]]:
        """Parse services.py to extract imports and classes"""
        tree = ast.parse(content)
        
        # Extract module-level imports
        imports = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.append(ast.get_source_segment(content, node))
        
        file_imports = '\n'.join(imports)
        
        # Extract classes with their code
        classes = {}
        lines = content.split('\n')
        
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name
                
                # Get class definition lines
                start_line = node.lineno - 1
                end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line + 1
                
                class_code = '\n'.join(lines[start_line:end_line])
                
                # Determine base class
                base_class = 'BaseService'
                if node.bases:
                    if isinstance(node.bases[0], ast.Name):
                        base_class = node.bases[0].id
                
                # Extract additional imports this class might need
                class_imports = self._extract_class_imports(class_code)
                
                classes[class_name] = {
                    'code': class_code,
                    'base_class': base_class,
                    'imports': class_imports,
                    'docstring': ast.get_docstring(node) or f"Service for {class_name}"
                }
        
        return file_imports, classes
    
    def _extract_class_imports(self, class_code: str) -> Set[str]:
        """Extract any special imports needed by this class"""
        imports = set()
        
        # Check for lazy imports inside methods
        lazy_import_pattern = r'from ([\w.]+) import ([\w, ]+)'
        matches = re.findall(lazy_import_pattern, class_code)
        for module, names in matches:
            imports.add(f"from {module} import {names}")
        
        return imports
    
    def _split_services(self, file_imports: str, classes: Dict[str, Dict]):
        """Split services into separate files"""
        for class_name, class_info in classes.items():
            # Generate filename (convert CamelCase to snake_case)
            filename = self._camel_to_snake(class_name) + '.py'
            filepath = os.path.join(self.services_dir, filename)
            
            # Build file content
            content = self._build_service_file(
                class_name=class_name,
                class_info=class_info,
                file_imports=file_imports
            )
            
            # Write file
            with open(filepath, 'w') as f:
                f.write(content)
            
            print(f"   ✅ Created: {filepath}")
    
    def _build_service_file(self, class_name: str, class_info: Dict, file_imports: str) -> str:
        """Build content for individual service file"""
        content = []
        
        # Header
        content.append('"""')
        content.append(f'{class_name} - Individual Service File')
        content.append('=' * 60)
        content.append('')
        content.append(f'{class_info["docstring"]}')
        content.append('')
        content.append('Auto-generated by Service Splitter')
        content.append(f'Date: {datetime.now().strftime("%Y-%m-%d")}')
        content.append('"""')
        content.append('')
        
        # Imports
        content.append('from __future__ import annotations')
        content.append('')
        
        # Add file-level imports (filtered to what's needed)
        needed_imports = self._filter_imports(file_imports, class_info)
        content.append(needed_imports)
        content.append('')
        
        # Class code
        content.append('')
        content.append(class_info['code'])
        content.append('')
        
        return '\n'.join(content)
    
    def _filter_imports(self, file_imports: str, class_info: Dict) -> str:
        """Filter imports to only include what's needed"""
        # For now, include all imports (can be optimized later)
        # In production, you'd analyze the class code to determine exact imports needed
        return file_imports
    
    def _create_init_file(self, classes: Dict[str, Dict]):
        """Create __init__.py with all service exports"""
        content = []
        
        # Header
        content.append('"""')
        content.append('Points Services - Service Layer Exports')
        content.append('=' * 60)
        content.append('')
        content.append('This module exports all point-related services.')
        content.append('')
        content.append('Auto-generated by Service Splitter')
        content.append(f'Date: {datetime.now().strftime("%Y-%m-%d")}')
        content.append('"""')
        content.append('')
        
        # Import each service
        for class_name in classes.keys():
            filename = self._camel_to_snake(class_name)
            content.append(f'from .{filename} import {class_name}')
        
        content.append('')
        content.append('')
        
        # __all__ export
        content.append('__all__ = [')
        for class_name in classes.keys():
            content.append(f'    "{class_name}",')
        content.append(']')
        content.append('')
        
        # Write __init__.py
        init_file = os.path.join(self.services_dir, '__init__.py')
        with open(init_file, 'w') as f:
            f.write('\n'.join(content))
        
        print(f"   ✅ Created: {init_file}")
    
    def _camel_to_snake(self, name: str) -> str:
        """Convert CamelCase to snake_case"""
        # Insert underscore before uppercase letters
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        # Insert underscore before uppercase letters followed by lowercase
        s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1)
        return s2.lower()


def main():
    """Main entry point"""
    splitter = ServiceSplitter(services_file='services.py')
    
    # Check if services.py exists
    if not os.path.exists(splitter.services_file):
        print("❌ Error: services.py not found in current directory!")
        print("   Please run this script from the points/ directory.")
        return
    
    # Run the splitter
    try:
        splitter.run()
    except Exception as e:
        print(f"\n❌ Error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        print("\n💡 Tip: Check the backup in services_backup/ if needed")


if __name__ == '__main__':
    main()
