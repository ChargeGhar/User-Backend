#!/usr/bin/env python3
"""
Django API Endpoints Documentation Generator

This script generates comprehensive API documentation by analyzing Django views, 
serializers, and services to create accurate endpoint documentation in the 
ChargeGhar template format.

Usage:
    python endpoints_docs.py --app <app_name>
    python endpoints_docs.py --app users
    python endpoints_docs.py --all  # Generate docs for all apps

Author: ChargeGhar Development Team
"""

from __future__ import annotations

import argparse
import ast
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


class DjangoViewAnalyzer:
    """Analyzes Django views to extract endpoint information."""
    
    def __init__(self, app_path: str):
        self.app_path = Path(app_path)
        self.views_file = self.app_path / 'views.py'
        self.urls_file = self.app_path / 'urls.py'
        self.serializers_file = self.app_path / 'serializers.py'
        
        # Analysis results
        self.endpoints = []
        self.view_classes = {}
        self.serializers = {}
        self.url_patterns = []
    
    def analyze(self) -> Dict[str, Any]:
        """Analyze all Django files to extract endpoint information."""
        print(f"📝 Analyzing {self.app_path.name} app...")
        
        self._analyze_views()
        self._analyze_urls()
        self._analyze_serializers()
        self._generate_endpoints()
        
        return {
            'app_name': self.app_path.name,
            'endpoints': self.endpoints,
            'view_classes': len(self.view_classes),
            'serializers': len(self.serializers)
        }
    
    def _analyze_views(self) -> None:
        """Analyze views.py to extract view classes and methods."""
        if not self.views_file.exists():
            return
        
        try:
            with open(self.views_file, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    self._extract_view_class(node)
                    
        except Exception as e:
            print(f"⚠️ Error analyzing views.py: {str(e)}")
    
    def _analyze_urls(self) -> None:
        """Analyze urls.py and views.py to extract URL patterns."""
        # First try to get patterns from views.py decorators
        self._extract_patterns_from_views()
        
        # Then supplement with urls.py if available
        if self.urls_file.exists():
            try:
                with open(self.urls_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract additional router registrations from urls.py
                router_patterns = re.findall(
                    r'@router\.register\(r["\']([^"\']*)["\'"].*?name=["\']([^"\']*)["\'"]',
                    content,
                    re.DOTALL
                )
                
                for pattern, name in router_patterns:
                    self.url_patterns.append({
                        'pattern': pattern,
                        'name': name,
                        'type': 'router'
                    })
                    
            except Exception as e:
                print(f"⚠️ Error analyzing urls.py: {str(e)}")
    
    def _extract_patterns_from_views(self) -> None:
        """Extract URL patterns from @router.register decorators in views.py."""
        if not self.views_file.exists():
            return
        
        try:
            with open(self.views_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract @router.register patterns from views.py
            # Pattern: @router.register(r"auth/otp/request", name="auth-otp-request")
            router_patterns = re.findall(
                r'@router\.register\(r["\']([^"\']*)["\'],\s*name=["\']([^"\']*)["\']',
                content,
                re.MULTILINE
            )
            
            for pattern, name in router_patterns:
                self.url_patterns.append({
                    'pattern': pattern,
                    'name': name,
                    'type': 'router'
                })
                
        except Exception as e:
            print(f"⚠️ Error extracting patterns from views.py: {str(e)}")
    
    def _analyze_serializers(self) -> None:
        """Analyze serializers.py to extract serializer information."""
        if not self.serializers_file.exists():
            return
        
        try:
            with open(self.serializers_file, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    if any('Serializer' in str(base) for base in node.bases):
                        self.serializers[node.name] = {
                            'name': node.name,
                            'docstring': ast.get_docstring(node)
                        }
                        
        except Exception as e:
            print(f"⚠️ Error analyzing serializers.py: {str(e)}")
    
    def _extract_view_class(self, node: ast.ClassDef) -> None:
        """Extract information from a view class."""
        class_info = {
            'name': node.name,
            'docstring': ast.get_docstring(node),
            'methods': [],
            'serializer_class': None,
            'permission_classes': [],
            'auth_required': False
        }
        
        # Extract methods and class attributes
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                if item.name.lower() in ['get', 'post', 'put', 'patch', 'delete']:
                    class_info['methods'].append(item.name.upper())
            elif isinstance(item, ast.Assign):
                self._extract_class_attributes(item, class_info)
        
        # Extract schema information from decorators
        for decorator in node.decorator_list:
            schema_info = self._extract_decorator_info(decorator)
            if schema_info:
                class_info.update(schema_info)
        
        self.view_classes[node.name] = class_info
    
    def _extract_class_attributes(self, node: ast.Assign, class_info: Dict[str, Any]) -> None:
        """Extract class attributes like serializer_class, permission_classes."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                attr_name = target.id
                
                if attr_name == 'serializer_class':
                    class_info['serializer_class'] = self._get_value_string(node.value)
                elif attr_name == 'permission_classes':
                    permissions = self._extract_list_values(node.value)
                    class_info['permission_classes'] = permissions
                    # Check for auth requirements
                    auth_permissions = ['IsAuthenticated', 'IsStaffPermission']
                    class_info['auth_required'] = any(
                        any(auth_perm in str(perm) for auth_perm in auth_permissions)
                        for perm in permissions
                    )
    
    def _extract_decorator_info(self, decorator: ast.AST) -> Optional[Dict[str, Any]]:
        """Extract decorator information, especially extend_schema."""
        if isinstance(decorator, ast.Call):
            func_name = self._get_name(decorator.func)
            
            if func_name == 'extend_schema':
                schema_info = {}
                for keyword in decorator.keywords:
                    if keyword.arg:
                        value = self._get_value_string(keyword.value)
                        if keyword.arg in ['summary', 'description', 'tags']:
                            schema_info[keyword.arg] = value
                return schema_info
        
        return None
    
    def _generate_endpoints(self) -> None:
        """Generate endpoint information by combining views and urls."""
        for url_pattern in self.url_patterns:
            pattern = url_pattern['pattern']
            name = url_pattern['name']
            
            # Find corresponding view class
            view_class = self._find_view_for_pattern(name)
            if view_class:
                endpoint_info = self._create_endpoint_info(pattern, view_class)
                if endpoint_info:
                    self.endpoints.append(endpoint_info)
    
    def _find_view_for_pattern(self, pattern_name: str) -> Optional[Dict[str, Any]]:
        """Find the view class that corresponds to a URL pattern."""
        # More sophisticated matching logic
        pattern_words = pattern_name.replace('-', ' ').replace('_', ' ').lower().split()
        
        best_match = None
        best_score = 0
        
        for view_name, view_class in self.view_classes.items():
            view_words = view_name.lower().replace('view', '').split()
            
            # Calculate matching score
            score = 0
            for pattern_word in pattern_words:
                for view_word in view_words:
                    if pattern_word in view_word or view_word in pattern_word:
                        score += 1
            
            # Normalize score by number of words
            if len(pattern_words) > 0:
                normalized_score = score / len(pattern_words)
                if normalized_score > best_score:
                    best_score = normalized_score
                    best_match = view_class
        
        return best_match if best_score > 0.3 else None
    
    def _create_endpoint_info(self, pattern: str, view_class: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create comprehensive endpoint information."""
        
        # Determine HTTP methods
        http_methods = view_class.get('methods', ['GET'])
        if not http_methods:
            http_methods = ['GET']
        
        # Convert pattern to API path
        api_path = f"/api/{pattern}"
        
        return {
            'path': api_path,
            'methods': http_methods,
            'view_class': view_class['name'],
            'serializer': view_class.get('serializer_class', ''),
            'auth_required': view_class.get('auth_required', False),
            'summary': view_class.get('summary', ''),
            'description': view_class.get('description', view_class.get('docstring', '')),
            'tags': view_class.get('tags', ['API'])
        }
    
    def _extract_list_values(self, node: ast.AST) -> List[str]:
        """Extract values from a list or tuple node."""
        if isinstance(node, (ast.List, ast.Tuple)):
            return [self._get_value_string(item) for item in node.elts]
        return []
    
    def _get_name(self, node: ast.AST) -> str:
        """Get name from various AST node types."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return str(node)
    
    def _get_value_string(self, node: ast.AST) -> str:
        """Get string representation of a value."""
        try:
            if hasattr(ast, 'unparse'):
                return ast.unparse(node)
            else:
                if isinstance(node, ast.Constant):
                    return repr(node.value)
                elif hasattr(node, 'id'):
                    return node.id
                return str(node)
        except:
            return str(node)


class EndpointDocumentationGenerator:
    """Generates API endpoint documentation in ChargeGhar template format."""
    
    def __init__(self, api_dir: str = "api"):
        self.api_dir = Path(api_dir)
        
        # Template for endpoint documentation
        self.endpoint_template = """## **{title}**

### **Endpoint**

`{method} {path}`

### **Description**

{description}

---

### **Request**

**Headers**

```json
{headers}
```

{request_body}

---

### **Response**

**Success**

```json
{{
  "success": true,
  "data": {{
    {response_data}
  }}
}}
```

**Error**

```json
{{
  "success": false,
  "error": {{
    "code": "ERROR_CODE",
    "message": "Error message"
  }}
}}
```

---

"""
    
    def get_available_apps(self) -> List[str]:
        """Get list of available Django apps."""
        if not self.api_dir.exists():
            return []
        
        apps = []
        for item in self.api_dir.iterdir():
            if item.is_dir() and not item.name.startswith('_'):
                if (item / 'views.py').exists():
                    apps.append(item.name)
        
        return sorted(apps)
    
    def generate_app_endpoint_docs(self, app_name: str) -> str:
        """Generate endpoint documentation for a specific app."""
        app_path = self.api_dir / app_name
        
        if not app_path.exists():
            raise ValueError(f"App '{app_name}' does not exist")
        
        print(f"📝 Generating endpoint documentation for '{app_name}' app...")
        
        # Analyze the app
        analyzer = DjangoViewAnalyzer(str(app_path))
        analysis_result = analyzer.analyze()
        
        # Generate markdown documentation
        markdown_content = self._generate_markdown(app_name, analysis_result)
        
        # Save to file
        output_file = app_path / "endpoints_docs.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print(f"✅ Documentation saved to: {output_file}")
        return str(output_file)
    
    def _generate_markdown(self, app_name: str, analysis_result: Dict[str, Any]) -> str:
        """Generate markdown documentation using ChargeGhar template format."""
        content = []
        
        # Header
        content.append(f"# **🔌 ChargeGhar {app_name.title()} API Specification**")
        content.append("")
        
        if not analysis_result['endpoints']:
            content.append("## **API Endpoints**")
            content.append("")
            content.append("*No endpoints detected. Please ensure views are properly configured.*")
            content.append("")
            return "\n".join(content)
        
        # Group endpoints by section
        sections = {}
        for endpoint in analysis_result['endpoints']:
            section = self._get_endpoint_section(endpoint['path'])
            if section not in sections:
                sections[section] = []
            sections[section].append(endpoint)
        
        # Generate documentation for each section
        for section_name, endpoints in sections.items():
            content.append(f"## **{section_name}**")
            content.append("")
            
            for endpoint in endpoints:
                content.extend(self._generate_endpoint_docs(endpoint))
        
        # Add common error codes
        content.extend(self._generate_common_errors())
        
        return "\n".join(content)
    
    def _generate_endpoint_docs(self, endpoint: Dict[str, Any]) -> List[str]:
        """Generate documentation for a single endpoint."""
        content = []
        
        # Title
        title = endpoint.get('summary') or f"{endpoint['view_class']} API"
        content.append(f"## **{title}**")
        content.append("")
        
        # Endpoint
        content.append("### **Endpoint**")
        content.append("")
        for method in endpoint['methods']:
            content.append(f"`{method} {endpoint['path']}`")
        content.append("")
        
        # Description
        content.append("### **Description**")
        content.append("")
        description = endpoint.get('description') or f"API endpoint handled by {endpoint['view_class']}"
        content.append(description)
        content.append("")
        content.append("---")
        content.append("")
        
        # Request
        content.append("### **Request**")
        content.append("")
        content.append("**Headers**")
        content.append("")
        content.append("```json")
        if endpoint['auth_required']:
            content.append("{")
            content.append('  "Authorization": "Bearer <access_token>",')
            content.append('  "Content-Type": "application/json"')
            content.append("}")
        else:
            content.append("{")
            content.append('  "Content-Type": "application/json"')
            content.append("}")
        content.append("```")
        content.append("")
        
        # Request body for POST/PUT methods
        if any(method in ['POST', 'PUT', 'PATCH'] for method in endpoint['methods']):
            content.append("**Request Body**")
            content.append("")
            content.append("```json")
            content.append("{")
            content.append('  "field1": "string",')
            content.append('  "field2": "value"')
            content.append("}")
            content.append("```")
            content.append("")
        
        content.append("---")
        content.append("")
        
        # Response
        content.append("### **Response**")
        content.append("")
        content.append("**Success**")
        content.append("")
        content.append("```json")
        content.append("{")
        content.append('  "success": true,')
        content.append('  "data": {')
        content.append('    // Response data')
        content.append('  }')
        content.append("}")
        content.append("```")
        content.append("")
        
        content.append("**Error**")
        content.append("")
        content.append("```json")
        content.append("{")
        content.append('  "success": false,')
        content.append('  "error": {')
        content.append('    "code": "ERROR_CODE",')
        content.append('    "message": "Error message"')
        content.append('  }')
        content.append("}")
        content.append("```")
        content.append("")
        content.append("---")
        content.append("")
        
        return content
    
    def _get_endpoint_section(self, path: str) -> str:
        """Determine the section for an endpoint based on its path."""
        if '/auth/' in path:
            return "Authentication Endpoints"
        elif '/users/' in path:
            return "User Management Endpoints"
        elif '/admin/' in path:
            return "Admin Endpoints"
        else:
            return "API Endpoints"
    
    def _generate_common_errors(self) -> List[str]:
        """Generate common error codes section."""
        content = []
        content.append("## **Common Error Codes**")
        content.append("")
        content.append("| Error Code | Description |")
        content.append("|------------|-------------|")
        content.append("| `VALIDATION_ERROR` | Request validation failed |")
        content.append("| `UNAUTHORIZED` | Authentication required |")
        content.append("| `PERMISSION_DENIED` | Insufficient permissions |")
        content.append("| `NOT_FOUND` | Resource not found |")
        content.append("| `RATE_LIMIT_EXCEEDED` | Too many requests |")
        content.append("")
        
        return content
    
    def generate_all_apps_documentation(self) -> List[str]:
        """Generate endpoint documentation for all available apps."""
        apps = self.get_available_apps()
        
        if not apps:
            print("❌ No Django apps found!")
            return []
        
        print(f"📚 Found {len(apps)} apps: {', '.join(apps)}")
        
        generated_files = []
        for app_name in apps:
            try:
                output_file = self.generate_app_endpoint_docs(app_name)
                generated_files.append(output_file)
            except Exception as e:
                print(f"❌ Failed to generate docs for '{app_name}': {str(e)}")
        
        return generated_files


def main():
    """Main entry point for the endpoint documentation generator."""
    parser = argparse.ArgumentParser(
        description="Generate API endpoint documentation for Django apps",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python endpoints_docs.py --app users          # Generate docs for users app
  python endpoints_docs.py --app payments       # Generate docs for payments app  
  python endpoints_docs.py --all                # Generate docs for all apps
  python endpoints_docs.py --list               # List available apps
        """
    )
    
    parser.add_argument('--app', type=str, help='Generate documentation for specific app')
    parser.add_argument('--all', action='store_true', help='Generate documentation for all apps')
    parser.add_argument('--list', action='store_true', help='List all available apps')
    
    args = parser.parse_args()
    
    # Initialize generator
    try:
        generator = EndpointDocumentationGenerator(api_dir='api')
    except Exception as e:
        print(f"❌ Failed to initialize generator: {str(e)}")
        return 1
    
    # Handle list command
    if args.list:
        apps = generator.get_available_apps()
        if apps:
            print(f"📋 Available Django apps ({len(apps)}):")
            for app in apps:
                print(f"  - {app}")
        else:
            print("❌ No Django apps found!")
        return 0
    
    # Handle single app documentation
    if args.app:
        try:
            output_file = generator.generate_app_endpoint_docs(args.app)
            print(f"\n🎉 Documentation generation completed!")
            print(f"📄 Output: {output_file}")
            return 0
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return 1
    
    # Handle all apps documentation
    if args.all:
        try:
            output_files = generator.generate_all_apps_documentation()
            print(f"\n🎉 Documentation generation completed!")
            print(f"📄 Generated {len(output_files)} files:")
            for file_path in output_files:
                print(f"  - {file_path}")
            return 0
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return 1
    
    # No valid arguments provided
    parser.print_help()
    return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())