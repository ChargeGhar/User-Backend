#!/usr/bin/env python3
"""
Django REST Framework Advanced Endpoint Analyzer
Features:
- List all endpoints with detailed info
- Analyze endpoint dependencies and usages
- Track which files, services, serializers, and models are used
- Generate comprehensive reports
- Safe cleanup with dry-run mode

1. List Endpoints - Multiple formats
bash# Table view (default)
python endpoints.py --list

# JSON format
python endpoints.py --list --format json

# Detailed view with all info
python endpoints.py --list --format detailed
2. Usage Analysis - Deep dependency tracking
bash# Show usage in terminal
python endpoints.py --usage --name users.user-profile

# Generate detailed markdown report
python endpoints.py --usage --name users.user-profile --report
"""

import os
import re
import ast
import json
import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
from datetime import datetime


class CodeAnalyzer:
    """Analyzes Python code for imports and function calls"""
    
    @staticmethod
    def extract_imports(file_path: Path) -> Dict[str, Set[str]]:
        """Extract all imports from a file"""
        imports = defaultdict(set)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
                
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports['direct'].add(alias.name)
                        
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    for alias in node.names:
                        imports['from'].add(f"{module}.{alias.name}")
                        
        except Exception as e:
            print(f"  ⚠ Error parsing imports from {file_path.name}: {e}")
            
        return imports
    
    @staticmethod
    def extract_function_calls(file_path: Path) -> Set[str]:
        """Extract all function/method calls from a file"""
        calls = set()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
                
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        calls.add(node.func.id)
                    elif isinstance(node.func, ast.Attribute):
                        calls.add(node.func.attr)
                        
        except Exception as e:
            print(f"  ⚠ Error parsing calls from {file_path.name}: {e}")
            
        return calls
    
    @staticmethod
    def extract_class_methods(file_path: Path, class_name: str) -> List[str]:
        """Extract all methods from a specific class"""
        methods = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
                
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            methods.append(item.name)
 
        except Exception as e:
            print(f"  ⚠ Error extracting methods: {e}")
            
        return methods


class EndpointAnalyzer:
    """Main analyzer for Django REST Framework endpoints"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        self.api_root = self.project_root / "api"
        self.endpoints = {}
        self.code_analyzer = CodeAnalyzer()
        
    def extract_endpoint_info(self, file_path: Path) -> List[Dict]:
        """Extract detailed endpoint information from view files"""
        endpoints = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)
                
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    endpoint_info = self._analyze_class(node, content, file_path)
                    if endpoint_info:
                        endpoints.append(endpoint_info)
                        
        except Exception as e:
            print(f"  ⚠ Error processing {file_path.name}: {e}")
            
        return endpoints
    
    def _analyze_class(self, class_node: ast.ClassDef, content: str, file_path: Path) -> Optional[Dict]:
        """Analyze a view class for endpoint information"""
        route_pattern = None
        name = None
        methods = []
        tags = []
        summary = ""
        description = ""
        permissions = []
        serializer = None
        
        # Extract decorators
        for decorator in class_node.decorator_list:
            if isinstance(decorator, ast.Call):
                # Router registration
                if hasattr(decorator.func, 'attr') and decorator.func.attr == 'register':
                    if len(decorator.args) >= 1:
                        route_pattern = ast.literal_eval(decorator.args[0])
                    for keyword in decorator.keywords:
                        if keyword.arg == 'name':
                            name = ast.literal_eval(keyword.value)
                            
                # Schema documentation
                if hasattr(decorator.func, 'attr') and decorator.func.attr == 'extend_schema':
                    for keyword in decorator.keywords:
                        if keyword.arg == 'tags' and isinstance(keyword.value, ast.List):
                            tags = [ast.literal_eval(el) for el in keyword.value.elts]
                        elif keyword.arg == 'summary':
                            summary = ast.literal_eval(keyword.value)
                        elif keyword.arg == 'description':
                            description = ast.literal_eval(keyword.value)
        
        # Extract class attributes
        for item in class_node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        if target.id == 'permission_classes':
                            permissions = self._extract_list_values(item.value)
                        elif target.id == 'serializer_class':
                            if isinstance(item.value, ast.Attribute):
                                serializer = item.value.attr
                            elif isinstance(item.value, ast.Name):
                                serializer = item.value.id
        
        # Extract HTTP methods
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef):
                method_name = item.name.lower()
                if method_name in ['get', 'post', 'put', 'patch', 'delete']:
                    docstring = ast.get_docstring(item) or ""
                    
                    # Analyze method body for service calls
                    service_calls = self._extract_service_calls(item)
                    
                    methods.append({
                        'method': method_name.upper(),
                        'description': docstring.strip(),
                        'service_calls': service_calls
                    })
        
        if route_pattern and methods:
            endpoint_id = name or f"{class_node.name.lower()}"
            
            return {
                'id': endpoint_id,
                'class_name': class_node.name,
                'route': route_pattern,
                'methods': methods,
                'tags': tags,
                'summary': summary,
                'description': description,
                'permissions': permissions,
                'serializer': serializer,
                'file': str(file_path.relative_to(self.project_root)),
                'app': file_path.parent.parent.name
            }
        
        return None
    
    def _extract_list_values(self, node: ast.AST) -> List[str]:
        """Extract values from a list node"""
        values = []
        if isinstance(node, ast.List):
            for el in node.elts:
                if isinstance(el, ast.Name):
                    values.append(el.id)
                elif isinstance(el, ast.Attribute):
                    values.append(el.attr)
        return values
    
    def _extract_service_calls(self, func_node: ast.FunctionDef) -> List[str]:
        """Extract service method calls from a function"""
        service_calls = []
        
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    # Look for service.method() patterns
                    if isinstance(node.func.value, ast.Name):
                        service_name = node.func.value.id
                        method_name = node.func.attr
                        if 'service' in service_name.lower():
                            service_calls.append(f"{service_name}.{method_name}()")
                            
        return service_calls
    
    def analyze_dependencies(self, endpoint: Dict) -> Dict:
        """Analyze all dependencies for an endpoint"""
        file_path = self.project_root / endpoint['file']
        app_path = self.api_root / endpoint['app']
        
        dependencies = {
            'imports': {},
            'services': [],
            'serializers': [],
            'models': [],
            'tasks': [],
            'permissions': endpoint['permissions'],
            'files_used': []
        }
        
        # Extract imports
        imports = self.code_analyzer.extract_imports(file_path)
        dependencies['imports'] = dict(imports)
        
        # Find service files
        services_path = app_path / 'services'
        if services_path.exists():
            for service_file in services_path.glob('*.py'):
                if service_file.name != '__init__.py':
                    dependencies['services'].append(str(service_file.relative_to(self.project_root)))
                    dependencies['files_used'].append(str(service_file.relative_to(self.project_root)))
        
        # Find serializers
        serializers_file = app_path / 'serializers.py'
        if serializers_file.exists():
            dependencies['serializers'].append(str(serializers_file.relative_to(self.project_root)))
            dependencies['files_used'].append(str(serializers_file.relative_to(self.project_root)))
        
        # Find models
        models_file = app_path / 'models.py'
        if models_file.exists():
            dependencies['models'].append(str(models_file.relative_to(self.project_root)))
            dependencies['files_used'].append(str(models_file.relative_to(self.project_root)))
        
        # Find tasks
        tasks_file = app_path / 'tasks.py'
        if tasks_file.exists():
            dependencies['tasks'].append(str(tasks_file.relative_to(self.project_root)))
            dependencies['files_used'].append(str(tasks_file.relative_to(self.project_root)))
        
        return dependencies
    
    def scan_project(self):
        """Scan entire project for endpoints"""
        print("\n🔍 Scanning project for endpoints...")
        print(f"📁 Project root: {self.project_root}")
        print(f"📁 API root: {self.api_root}\n")
        
        # Scan all view files
        for views_dir in self.api_root.rglob("views"):
            if views_dir.is_dir():
                app_name = views_dir.parent.name
                print(f"  📦 Scanning app: {app_name}")
                
                for view_file in views_dir.glob("*.py"):
                    if view_file.name != "__init__.py":
                        print(f"    📄 {view_file.name}")
                        endpoints = self.extract_endpoint_info(view_file)
                        
                        for endpoint in endpoints:
                            endpoint_id = f"{app_name}.{endpoint['id']}"
                            self.endpoints[endpoint_id] = endpoint
                            print(f"      ✓ Found: {endpoint['class_name']}")
        
        print(f"\n✅ Found {len(self.endpoints)} endpoints across {len(set(e['app'] for e in self.endpoints.values()))} apps\n")
    
    def list_endpoints(self, format_type: str = 'table'):
        """List all endpoints in various formats"""
        if not self.endpoints:
            print("❌ No endpoints found. Run scan first.")
            return
        
        if format_type == 'table':
            self._list_table()
        elif format_type == 'json':
            self._list_json()
        elif format_type == 'detailed':
            self._list_detailed()
    
    def _list_table(self):
        """List endpoints in table format"""
        print("\n" + "="*120)
        print(f"{'ID':<30} {'ROUTE':<35} {'METHODS':<20} {'APP':<15} {'TAG':<20}")
        print("="*120)
        
        for endpoint_id, endpoint in sorted(self.endpoints.items()):
            methods = ', '.join([m['method'] for m in endpoint['methods']])
            tag = endpoint['tags'][0] if endpoint['tags'] else '-'
            route = f"/api/{endpoint['route']}/"
            
            print(f"{endpoint_id:<30} {route:<35} {methods:<20} {endpoint['app']:<15} {tag:<20}")
        
        print("="*120)
        print(f"\nTotal: {len(self.endpoints)} endpoints\n")
    
    def _list_json(self):
        """List endpoints in JSON format"""
        output = {
            'total': len(self.endpoints),
            'endpoints': {}
        }
        
        for endpoint_id, endpoint in self.endpoints.items():
            output['endpoints'][endpoint_id] = {
                'route': endpoint['route'],
                'methods': [m['method'] for m in endpoint['methods']],
                'app': endpoint['app'],
                'class': endpoint['class_name'],
                'tags': endpoint['tags']
            }
        
        print(json.dumps(output, indent=2))
    
    def _list_detailed(self):
        """List endpoints with detailed information"""
        for endpoint_id, endpoint in sorted(self.endpoints.items()):
            print("\n" + "="*100)
            print(f"📍 {endpoint_id.upper()}")
            print("="*100)
            print(f"Class:       {endpoint['class_name']}")
            print(f"Route:       /api/{endpoint['route']}/")
            print(f"App:         {endpoint['app']}")
            print(f"File:        {endpoint['file']}")
            print(f"Tags:        {', '.join(endpoint['tags']) if endpoint['tags'] else 'None'}")
            print(f"Permissions: {', '.join(endpoint['permissions']) if endpoint['permissions'] else 'None'}")
            print(f"Serializer:  {endpoint['serializer'] or 'None'}")
            
            if endpoint['summary']:
                print(f"Summary:     {endpoint['summary']}")
            
            print(f"\nMethods ({len(endpoint['methods'])}):")
            for method in endpoint['methods']:
                print(f"  • {method['method']}")
                if method['description']:
                    print(f"    {method['description']}")
                if method['service_calls']:
                    print(f"    Services: {', '.join(method['service_calls'])}")
            
            print()
    
    def show_usage(self, endpoint_name: str, generate_report: bool = False):
        """Show detailed usage analysis for an endpoint"""
        if endpoint_name not in self.endpoints:
            print(f"❌ Endpoint '{endpoint_name}' not found")
            print(f"\n💡 Available endpoints:")
            for ep_id in sorted(self.endpoints.keys())[:10]:
                print(f"   • {ep_id}")
            if len(self.endpoints) > 10:
                print(f"   ... and {len(self.endpoints) - 10} more")
            return
        
        endpoint = self.endpoints[endpoint_name]
        print(f"\n{'='*100}")
        print(f"📊 USAGE ANALYSIS: {endpoint_name}")
        print(f"{'='*100}")
        
        # Basic info
        print(f"\n📍 Basic Information")
        print(f"   Class:       {endpoint['class_name']}")
        print(f"   Route:       /api/{endpoint['route']}/")
        print(f"   App:         {endpoint['app']}")
        print(f"   File:        {endpoint['file']}")
        print(f"   Methods:     {', '.join([m['method'] for m in endpoint['methods']])}")
        
        # Analyze dependencies
        print(f"\n🔗 Dependency Analysis")
        dependencies = self.analyze_dependencies(endpoint)
        
        print(f"\n   📦 Services Used:")
        if dependencies['services']:
            for service in dependencies['services']:
                print(f"      • {service}")
        else:
            print(f"      (none)")
        
        print(f"\n   📝 Serializers:")
        if dependencies['serializers']:
            for serializer in dependencies['serializers']:
                print(f"      • {serializer}")
        else:
            print(f"      (none)")
        
        print(f"\n   🗄️  Models:")
        if dependencies['models']:
            for model in dependencies['models']:
                print(f"      • {model}")
        else:
            print(f"      (none)")
        
        print(f"\n   ⚡ Tasks:")
        if dependencies['tasks']:
            for task in dependencies['tasks']:
                print(f"      • {task}")
        else:
            print(f"      (none)")
        
        print(f"\n   🔐 Permissions:")
        if dependencies['permissions']:
            for perm in dependencies['permissions']:
                print(f"      • {perm}")
        else:
            print(f"      (none)")
        
        print(f"\n   📥 Imports:")
        if dependencies['imports'].get('from'):
            for imp in sorted(dependencies['imports']['from'])[:10]:
                print(f"      • {imp}")
            if len(dependencies['imports']['from']) > 10:
                print(f"      ... and {len(dependencies['imports']['from']) - 10} more")
        
        # Method details
        print(f"\n🎯 Method Details")
        for method in endpoint['methods']:
            print(f"\n   {method['method']}:")
            if method['description']:
                print(f"      Description: {method['description']}")
            if method['service_calls']:
                print(f"      Service calls:")
                for call in method['service_calls']:
                    print(f"         → {call}")
        
        # Files involved
        print(f"\n📁 Files Involved ({len(dependencies['files_used'])}):")
        for file in dependencies['files_used']:
            print(f"   • {file}")
        
        print(f"\n{'='*100}\n")
        
        # Generate report if requested
        if generate_report:
            self._generate_usage_report(endpoint_name, endpoint, dependencies)
    
    def _generate_usage_report(self, endpoint_name: str, endpoint: Dict, dependencies: Dict):
        """Generate a detailed markdown report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"endpoint_report_{endpoint['app']}_{endpoint['id']}_{timestamp}.md"
        
        with open(filename, 'w') as f:
            f.write(f"# Endpoint Usage Report: {endpoint_name}\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")
            
            f.write("## Basic Information\n\n")
            f.write(f"- **Endpoint ID:** `{endpoint_name}`\n")
            f.write(f"- **Class:** `{endpoint['class_name']}`\n")
            f.write(f"- **Route:** `/api/{endpoint['route']}/`\n")
            f.write(f"- **App:** `{endpoint['app']}`\n")
            f.write(f"- **File:** `{endpoint['file']}`\n")
            f.write(f"- **Tags:** {', '.join(endpoint['tags']) if endpoint['tags'] else 'None'}\n\n")
            
            if endpoint['summary']:
                f.write(f"**Summary:** {endpoint['summary']}\n\n")
            if endpoint['description']:
                f.write(f"**Description:** {endpoint['description']}\n\n")
            
            f.write("## HTTP Methods\n\n")
            for method in endpoint['methods']:
                f.write(f"### {method['method']}\n\n")
                if method['description']:
                    f.write(f"{method['description']}\n\n")
                if method['service_calls']:
                    f.write("**Service Calls:**\n")
                    for call in method['service_calls']:
                        f.write(f"- `{call}`\n")
                    f.write("\n")
            
            f.write("## Dependencies\n\n")
            
            f.write("### Services\n\n")
            if dependencies['services']:
                for service in dependencies['services']:
                    f.write(f"- `{service}`\n")
            else:
                f.write("No services used\n")
            f.write("\n")
            
            f.write("### Serializers\n\n")
            if dependencies['serializers']:
                for serializer in dependencies['serializers']:
                    f.write(f"- `{serializer}`\n")
            else:
                f.write("No serializers\n")
            f.write("\n")
            
            f.write("### Models\n\n")
            if dependencies['models']:
                for model in dependencies['models']:
                    f.write(f"- `{model}`\n")
            else:
                f.write("No models\n")
            f.write("\n")
            
            f.write("### Permissions\n\n")
            if dependencies['permissions']:
                for perm in dependencies['permissions']:
                    f.write(f"- `{perm}`\n")
            else:
                f.write("No explicit permissions\n")
            f.write("\n")
            
            f.write("## Files Involved\n\n")
            for file in dependencies['files_used']:
                f.write(f"- `{file}`\n")
            f.write("\n")
            
            f.write("---\n\n")
            f.write("*Report generated by Django Endpoint Analyzer*\n")
        
        print(f"✅ Report generated: {filename}")
    
    def cleanup_endpoint(self, endpoint_name: str, dry_run: bool = True):
        """Remove an endpoint and optionally its dependencies"""
        if endpoint_name not in self.endpoints:
            print(f"❌ Endpoint '{endpoint_name}' not found")
            return
        
        endpoint = self.endpoints[endpoint_name]
        file_path = self.project_root / endpoint['file']
        
        if dry_run:
            print(f"\n🔍 DRY RUN - No files will be modified\n")
        else:
            print(f"\n⚠️  EXECUTE MODE - Files will be modified!\n")
        
        print(f"{'='*100}")
        print(f"🗑️  CLEANUP PLAN: {endpoint_name}")
        print(f"{'='*100}\n")
        
        print(f"📍 Target Endpoint:")
        print(f"   Class:  {endpoint['class_name']}")
        print(f"   File:   {endpoint['file']}")
        print(f"   Route:  /api/{endpoint['route']}/\n")
        
        # Analyze what will be removed
        dependencies = self.analyze_dependencies(endpoint)
        
        print(f"📋 Actions to perform:\n")
        print(f"   1. Remove class '{endpoint['class_name']}' from {file_path.name}")
        print(f"   2. Remove URL pattern for '{endpoint['route']}'")
        
        if not dry_run:
            confirm = input(f"\n⚠️  Are you sure you want to delete this endpoint? (yes/no): ")
            if confirm.lower() != 'yes':
                print("❌ Cleanup cancelled")
                return
            
            try:
                # Backup original file
                backup_path = file_path.with_suffix('.py.backup')
                import shutil
                shutil.copy2(file_path, backup_path)
                print(f"\n✅ Created backup: {backup_path}")
                
                # Remove class from file
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # This is a simple implementation - you might want to use AST for better handling
                print(f"⚠️  Manual cleanup required:")
                print(f"   1. Remove '{endpoint['class_name']}' class from {file_path}")
                print(f"   2. Remove corresponding URL pattern")
                print(f"   3. Check for unused imports")
                print(f"\n💡 Backup created for safety. Review changes carefully!")
                
            except Exception as e:
                print(f"❌ Error during cleanup: {e}")
        else:
            print(f"\n💡 Run with --execute to perform actual cleanup")
            print(f"⚠️  Always review changes carefully!")
        
        print(f"\n{'='*100}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Django REST Framework Endpoint Analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all endpoints
  python endpoints.py --list
  python endpoints.py --list --format json
  python endpoints.py --list --format detailed
  
  # Analyze specific endpoint
  python endpoints.py --usage --name users.user-profile
  python endpoints.py --usage --name users.user-profile --report
  
  # Cleanup endpoint
  python endpoints.py --cleanup --name users.user-kyc --dry
  python endpoints.py --cleanup --name users.user-kyc --execute
        """
    )
    
    parser.add_argument('--list', action='store_true', help='List all endpoints')
    parser.add_argument('--format', choices=['table', 'json', 'detailed'], default='table',
                       help='Output format for listing (default: table)')
    
    parser.add_argument('--usage', action='store_true', help='Show endpoint usage analysis')
    parser.add_argument('--name', type=str, help='Endpoint name (e.g., users.user-profile)')
    parser.add_argument('--report', action='store_true', help='Generate detailed markdown report')
    
    parser.add_argument('--cleanup', action='store_true', help='Cleanup/remove endpoint')
    parser.add_argument('--dry', action='store_true', help='Dry run mode (no actual changes)')
    parser.add_argument('--execute', action='store_true', help='Execute cleanup (modifies files)')
    
    args = parser.parse_args()
    
    # Initialize analyzer
    print("\n" + "="*100)
    print("🚀 Django REST Framework Endpoint Analyzer")
    print("="*100)
    
    analyzer = EndpointAnalyzer(".")
    analyzer.scan_project()
    
    # Execute requested action
    if args.list:
        analyzer.list_endpoints(args.format)
        
    elif args.usage:
        if not args.name:
            print("❌ Error: --name required for --usage")
            return
        analyzer.show_usage(args.name, args.report)
        
    elif args.cleanup:
        if not args.name:
            print("❌ Error: --name required for --cleanup")
            return
        
        if args.execute and args.dry:
            print("❌ Error: Cannot use both --execute and --dry")
            return
        
        dry_run = not args.execute
        analyzer.cleanup_endpoint(args.name, dry_run)
        
    else:
        print("\n💡 No action specified. Use --list, --usage, or --cleanup")
        print("   Run with --help for more information\n")


if __name__ == "__main__":
    main()