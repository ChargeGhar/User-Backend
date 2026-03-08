#!/usr/bin/env python3
"""
Django App Structure Generator
Generates detailed structure documentation for views, services, and serializers

Usage:
    python structure.py --list                     # List all apps
    python structure.py --app users                # Show users app structure
    python structure.py --app users --dir views / services    # Show only views / services
    python structure.py --app users --save         # Save to files
    python structure.py --all                      # Generate for all apps
"""

import os
import re
import ast
import argparse
from pathlib import Path
from typing import List, Dict, Tuple, Optional


class StructureAnalyzer:
    """Analyzes Django app structure and generates documentation"""
    
    def __init__(self, base_path: str = "api"):
        self.base_path = Path(base_path)
        self.apps = self._discover_apps()
    
    def _discover_apps(self) -> List[str]:
        """Discover all Django apps in the api directory"""
        if not self.base_path.exists():
            return []
        
        apps = []
        for item in self.base_path.iterdir():
            if item.is_dir() and not item.name.startswith('_'):
                # Check if it's a Django app (has models.py or apps.py)
                if (item / 'models.py').exists() or (item / 'apps.py').exists():
                    apps.append(item.name)
        return sorted(apps)
    
    def analyze_views(self, app_name: str) -> Dict:
        """Analyze views structure"""
        app_path = self.base_path / app_name
        views_path = app_path / 'views'
        views_file = app_path / 'views.py'
        
        result = {
            'type': None,
            'files': [],
            'classes': [],
            'total_files': 0,
            'total_classes': 0
        }
        
        if views_path.exists() and views_path.is_dir():
            result['type'] = 'folder'
            result['files'] = self._analyze_views_folder(views_path)
            result['total_files'] = len([f for f in result['files'] if f['name'] != '__init__.py'])
            result['total_classes'] = sum(len(f['classes']) for f in result['files'])
        elif views_file.exists():
            result['type'] = 'file'
            classes = self._extract_view_classes(views_file)
            result['classes'] = classes
            result['total_files'] = 1
            result['total_classes'] = len(classes)
        
        return result
    
    def _analyze_views_folder(self, views_path: Path) -> List[Dict]:
        """Analyze views folder structure"""
        files = []
        
        for file_path in sorted(views_path.glob('*.py')):
            if file_path.name.startswith('_') and file_path.name != '__init__.py':
                continue
            
            classes = self._extract_view_classes(file_path)
            description = self._extract_file_docstring(file_path)
            
            files.append({
                'name': file_path.name,
                'description': description,
                'classes': classes,
                'class_count': len(classes)
            })
        
        return files
    
    def analyze_services(self, app_name: str) -> Dict:
        """Analyze services structure"""
        app_path = self.base_path / app_name
        services_path = app_path / 'services'
        services_file = app_path / 'services.py'
        
        result = {
            'type': None,
            'files': [],
            'classes': [],
            'total_files': 0,
            'total_classes': 0,
            'total_methods': 0
        }
        
        if services_path.exists() and services_path.is_dir():
            result['type'] = 'folder'
            result['files'] = self._analyze_services_folder(services_path)
            result['total_files'] = len([f for f in result['files'] if f['name'] != '__init__.py'])
            result['total_classes'] = sum(len(f['classes']) for f in result['files'])
            result['total_methods'] = sum(
                sum(len(c['methods']) for c in f['classes']) 
                for f in result['files']
            )
        elif services_file.exists():
            result['type'] = 'file'
            classes = self._extract_service_classes(services_file)
            result['classes'] = classes
            result['total_files'] = 1
            result['total_classes'] = len(classes)
            result['total_methods'] = sum(len(c['methods']) for c in classes)
        
        return result
    
    def _analyze_services_folder(self, services_path: Path) -> List[Dict]:
        """Analyze services folder structure"""
        files = []
        
        for file_path in sorted(services_path.glob('*.py')):
            if file_path.name.startswith('_') and file_path.name != '__init__.py':
                continue
            
            classes = self._extract_service_classes(file_path)
            description = self._extract_file_docstring(file_path)
            
            files.append({
                'name': file_path.name,
                'description': description,
                'classes': classes,
                'class_count': len(classes)
            })
        
        return files
    
    def analyze_serializers(self, app_name: str) -> Dict:
        """Analyze serializers structure"""
        app_path = self.base_path / app_name
        serializers_file = app_path / 'serializers.py'
        
        result = {
            'type': None,
            'serializers': [],
            'categories': {},
            'total_serializers': 0,
            'line_count': 0
        }
        
        if serializers_file.exists():
            result['type'] = 'file'
            result['serializers'] = self._extract_serializers(serializers_file)
            result['categories'] = self._categorize_serializers(result['serializers'])
            result['total_serializers'] = len(result['serializers'])
            result['line_count'] = len(serializers_file.read_text().splitlines())
        
        return result
    
    def _extract_view_classes(self, file_path: Path) -> List[str]:
        """Extract view class names from a Python file"""
        try:
            content = file_path.read_text()
            tree = ast.parse(content)
            
            classes = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if it's a view class
                    base_names = [self._get_name(base) for base in node.bases]
                    if any('View' in name or 'ViewSet' in name for name in base_names):
                        classes.append(node.name)
            
            return classes
        except Exception as e:
            return []
    
    def _extract_service_classes(self, file_path: Path) -> List[Dict]:
        """Extract service classes with their methods"""
        try:
            content = file_path.read_text()
            tree = ast.parse(content)
            
            classes = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if it's a service class
                    if 'Service' in node.name or any('Service' in self._get_name(base) for base in node.bases):
                        methods = []
                        for item in node.body:
                            if isinstance(item, ast.FunctionDef):
                                # Skip magic methods except __init__
                                if not item.name.startswith('__') or item.name == '__init__':
                                    methods.append(item.name)
                        
                        classes.append({
                            'name': node.name,
                            'methods': methods
                        })
            
            return classes
        except Exception as e:
            return []
    
    def _extract_serializers(self, file_path: Path) -> List[str]:
        """Extract serializer class names"""
        try:
            content = file_path.read_text()
            tree = ast.parse(content)
            
            serializers = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if it's a serializer class
                    if 'Serializer' in node.name:
                        serializers.append(node.name)
            
            return serializers
        except Exception as e:
            return []
    
    def _categorize_serializers(self, serializers: List[str]) -> Dict[str, List[str]]:
        """Categorize serializers by common prefixes"""
        categories = {}
        
        # Common categories
        category_keywords = {
            'Authentication Serializers': ['Login', 'Register', 'OTP', 'Auth', 'Token', 'Password'],
            'Profile Serializers': ['Profile', 'KYC', 'Device'],
            'User Serializers': ['User'],
            'Payment Serializers': ['Payment', 'Transaction', 'Wallet', 'Refund'],
            'Station Serializers': ['Station', 'PowerBank'],
            'Rental Serializers': ['Rental', 'Package'],
            'Point Serializers': ['Point', 'Referral'],
            'Notification Serializers': ['Notification'],
            'Admin Serializers': ['Admin'],
            'Utility Serializers': ['Filter', 'Analytics', 'List', 'Detail', 'Basic', 'Response']
        }
        
        categorized = set()
        
        for category, keywords in category_keywords.items():
            matches = []
            for serializer in serializers:
                if serializer not in categorized:
                    for keyword in keywords:
                        if keyword in serializer:
                            matches.append(serializer)
                            categorized.add(serializer)
                            break
            
            if matches:
                categories[category] = matches
        
        # Uncategorized
        uncategorized = [s for s in serializers if s not in categorized]
        if uncategorized:
            categories['Other Serializers'] = uncategorized
        
        return categories
    
    def _extract_file_docstring(self, file_path: Path) -> str:
        """Extract file docstring"""
        try:
            content = file_path.read_text()
            tree = ast.parse(content)
            docstring = ast.get_docstring(tree)
            return docstring if docstring else ""
        except:
            return ""
    
    def _get_name(self, node) -> str:
        """Get name from AST node"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        return ""
    
    def format_views_structure(self, app_name: str, data: Dict) -> str:
        """Format views structure output"""
        if data['type'] is None:
            return f"api/{app_name}/views/\n└── ✗ No views found\n"
        
        lines = []
        lines.append(f"api/{app_name}/views/")
        
        if data['type'] == 'file':
            lines.append(f"└── views.py                    # Single file ({data['total_classes']} classes)")
            for cls in data['classes']:
                lines.append(f"    └── {cls}")
        else:
            files = data['files']
            for i, file_info in enumerate(files):
                is_last = (i == len(files) - 1)
                prefix = "└──" if is_last else "├──"
                
                desc = file_info['description'] or "View classes"
                count_info = f"({file_info['class_count']} classes)" if file_info['class_count'] > 0 else ""
                
                if file_info['name'] == '__init__.py':
                    lines.append(f"{prefix} {file_info['name']:<26} # Router merge")
                else:
                    lines.append(f"{prefix} {file_info['name']:<26} # {desc} {count_info}")
                
                # Add classes
                for j, cls in enumerate(file_info['classes']):
                    is_last_class = (j == len(file_info['classes']) - 1)
                    cls_prefix = "└──" if is_last_class else "├──"
                    indent = "    " if is_last else "│   "
                    lines.append(f"{indent}{cls_prefix} {cls}")
        
        lines.append(f"\nTotal: {data['total_files']} files, {data['total_classes']} view classes")
        return '\n'.join(lines)
    
    def format_services_structure(self, app_name: str, data: Dict) -> str:
        """Format services structure output"""
        if data['type'] is None:
            return f"api/{app_name}/services/\n└── ✗ No services found\n"
        
        lines = []
        lines.append(f"api/{app_name}/services/")
        
        if data['type'] == 'file':
            lines.append(f"└── services.py                # Single file ({data['total_classes']} classes)")
            for cls_info in data['classes']:
                lines.append(f"    └── {cls_info['name']}")
                for method in cls_info['methods']:
                    lines.append(f"        ├── {method}()")
        else:
            files = data['files']
            for i, file_info in enumerate(files):
                is_last_file = (i == len(files) - 1)
                prefix = "└──" if is_last_file else "├──"
                
                desc = file_info['description'] or "Service operations"
                
                if file_info['name'] == '__init__.py':
                    lines.append(f"{prefix} {file_info['name']:<30} # Exports")
                else:
                    lines.append(f"{prefix} {file_info['name']:<30} # {desc}")
                
                # Add classes and methods
                for j, cls_info in enumerate(file_info['classes']):
                    is_last_class = (j == len(file_info['classes']) - 1)
                    cls_prefix = "└──" if is_last_class else "├──"
                    indent1 = "    " if is_last_file else "│   "
                    
                    lines.append(f"{indent1}{cls_prefix} {cls_info['name']}")
                    
                    # Add methods
                    for k, method in enumerate(cls_info['methods']):
                        is_last_method = (k == len(cls_info['methods']) - 1)
                        method_prefix = "└──" if is_last_method else "├──"
                        indent2 = "    " if is_last_class else "│   "
                        indent = indent1 + indent2
                        
                        lines.append(f"{indent}{method_prefix} {method}()")
        
        lines.append(f"\nTotal: {data['total_files']} files, {data['total_classes']} service classes, {data['total_methods']} methods")
        return '\n'.join(lines)
    
    def format_serializers_structure(self, app_name: str, data: Dict) -> str:
        """Format serializers structure output"""
        if data['type'] is None:
            return f"api/{app_name}/serializers.py\n└── ✗ No serializers found\n"
        
        lines = []
        lines.append(f"api/{app_name}/serializers.py          # Single file ({data['line_count']} lines)")
        
        categories = data['categories']
        category_list = list(categories.items())
        
        for i, (category, serializers) in enumerate(category_list):
            is_last_category = (i == len(category_list) - 1)
            cat_prefix = "└──" if is_last_category else "├──"
            
            lines.append(f"{cat_prefix} {category}")
            
            for j, serializer in enumerate(serializers):
                is_last = (j == len(serializers) - 1)
                ser_prefix = "└──" if is_last else "├──"
                indent = "    " if is_last_category else "│   "
                
                lines.append(f"{indent}{ser_prefix} {serializer}")
        
        lines.append(f"\nTotal: 1 file, {data['total_serializers']} serializers ({len(categories)} categories)")
        return '\n'.join(lines)
    
    def list_all_apps(self) -> str:
        """List all apps with summary"""
        lines = []
        lines.append("═" * 70)
        lines.append("                    ALL APPS SUMMARY")
        lines.append("═" * 70)
        lines.append("")
        lines.append(f"{'App':<15} {'Views':<18} {'Services':<18} {'Serializers':<15}")
        lines.append("─" * 70)
        
        for app in self.apps:
            views_data = self.analyze_views(app)
            services_data = self.analyze_services(app)
            serializers_data = self.analyze_serializers(app)
            
            # Views summary
            if views_data['type'] == 'folder':
                views_str = f"{views_data['total_files']} files"
            elif views_data['type'] == 'file':
                views_str = "1 file"
            else:
                views_str = "None"
            
            # Services summary
            if services_data['type'] == 'folder':
                services_str = f"{services_data['total_files']} files"
            elif services_data['type'] == 'file':
                services_str = "1 file"
            else:
                services_str = "None"
            
            # Serializers summary
            serializers_str = "1 file" if serializers_data['type'] == 'file' else "None"
            
            lines.append(f"{app:<15} {views_str:<18} {services_str:<18} {serializers_str:<15}")
        
        lines.append("")
        lines.append(f"Total Apps: {len(self.apps)}")
        return '\n'.join(lines)
    
    def generate_app_structure(self, app_name: str, component: Optional[str] = None) -> str:
        """Generate structure for a specific app"""
        if app_name not in self.apps:
            return f"❌ Error: App '{app_name}' not found. Available apps: {', '.join(self.apps)}"
        
        output = []
        
        # Header
        output.append("═" * 70)
        output.append(f"📦 APP: {app_name}")
        output.append("═" * 70)
        output.append("")
        
        # Views
        if component is None or component == 'views':
            views_data = self.analyze_views(app_name)
            output.append("📄 VIEWS")
            output.append("━" * 70)
            output.append(self.format_views_structure(app_name, views_data))
            output.append("")
        
        # Services
        if component is None or component == 'services':
            services_data = self.analyze_services(app_name)
            output.append("⚙️  SERVICES")
            output.append("━" * 70)
            output.append(self.format_services_structure(app_name, services_data))
            output.append("")
        
        # Serializers
        if component is None or component == 'serializers':
            serializers_data = self.analyze_serializers(app_name)
            output.append("📋 SERIALIZERS")
            output.append("━" * 70)
            output.append(self.format_serializers_structure(app_name, serializers_data))
            output.append("")
        
        return '\n'.join(output)
    
    def save_structure_files(self, app_name: str) -> List[str]:
        """Save structure to files in relevant directories"""
        if app_name not in self.apps:
            return []
        
        saved_files = []
        app_path = self.base_path / app_name
        
        # Save views structure
        views_data = self.analyze_views(app_name)
        if views_data['type'] == 'folder':
            views_file = app_path / 'views' / 'structure.txt'
            views_file.write_text(self.format_views_structure(app_name, views_data))
            saved_files.append(str(views_file))
        
        # Save services structure
        services_data = self.analyze_services(app_name)
        if services_data['type'] == 'folder':
            services_file = app_path / 'services' / 'structure.txt'
            services_file.write_text(self.format_services_structure(app_name, services_data))
            saved_files.append(str(services_file))
        
        # Save serializers structure
        serializers_data = self.analyze_serializers(app_name)
        if serializers_data['type'] == 'file':
            serializers_file = app_path / 'serializers_structure.txt'
            serializers_file.write_text(self.format_serializers_structure(app_name, serializers_data))
            saved_files.append(str(serializers_file))
        
        # Save complete structure
        complete_file = app_path / 'APP_STRUCTURE.txt'
        complete_file.write_text(self.generate_app_structure(app_name))
        saved_files.append(str(complete_file))
        
        return saved_files


def main():
    parser = argparse.ArgumentParser(description='Django App Structure Generator')
    parser.add_argument('--list', action='store_true', help='List all apps')
    parser.add_argument('--app', type=str, help='Specify app name')
    parser.add_argument('--dir', type=str, choices=['views', 'services', 'serializers'], 
                       help='Show specific component')
    parser.add_argument('--save', action='store_true', help='Save to files')
    parser.add_argument('--all', action='store_true', help='Generate for all apps')
    
    args = parser.parse_args()
    
    analyzer = StructureAnalyzer()
    
    # List all apps
    if args.list:
        print(analyzer.list_all_apps())
        return
    
    # Generate for all apps
    if args.all:
        print("Generating structure files for all apps...")
        print("")
        for app in analyzer.apps:
            files = analyzer.save_structure_files(app)
            if files:
                print(f"✅ {app}:")
                for f in files:
                    print(f"   - {f}")
        print("")
        print(f"✅ Generated structure files for {len(analyzer.apps)} apps")
        return
    
    # Show specific app
    if args.app:
        if args.save:
            files = analyzer.save_structure_files(args.app)
            if files:
                print(f"✅ Saved structure files for '{args.app}':")
                for f in files:
                    print(f"   - {f}")
            else:
                print(f"❌ No structure files generated for '{args.app}'")
        else:
            output = analyzer.generate_app_structure(args.app, args.dir)
            print(output)
        return
    
    # No arguments - show help
    parser.print_help()


if __name__ == '__main__':
    main()
