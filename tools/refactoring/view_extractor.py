#!/usr/bin/env python3
"""
View Class Extractor and Issue Identifier for ChargeGhar Django Views

This script acts as an intermediary between developers and codebase analysis.
It identifies error handling issues and extracts complete view classes for manual review and fixing.

The script provides:
1. Issue identification with severity levels
2. Complete view class extraction 
3. Context and suggestions for AI-assisted fixing
4. Clean presentation for manual review

Usage:
    python view_extractor.py --analyze --app payments
    python view_extractor.py --extract --app payments --view RefundListView
    python view_extractor.py --scan-all --severity high
    python view_extractor.py --extract-issues --app rentals

Examples:
    # Analyze specific app for issues
    python view_extractor.py --analyze --app payments
    
    # Extract specific problematic view class
    python view_extractor.py --extract --app payments --view RefundListView
    
    # Scan all apps and extract high-severity issues
    python view_extractor.py --scan-all --severity high
    
    # Extract all problematic views from an app
    python view_extractor.py --extract-issues --app rentals
"""

import os
import re
import ast
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ViewIssue:
    """Data class for view issues"""
    app_name: str
    file_path: str
    view_name: str
    method_name: str
    line_number: int
    issue_type: str
    severity: str  # 'critical', 'high', 'medium', 'low'
    description: str
    current_pattern: str
    suggested_pattern: str
    context: Dict = field(default_factory=dict)

@dataclass
class ViewClass:
    """Data class for extracted view classes"""
    app_name: str
    file_path: str
    class_name: str
    line_start: int
    line_end: int
    source_code: str
    imports_needed: List[str]
    inheritance: List[str]
    methods: List[str]
    decorators: List[str]
    issues: List[ViewIssue]

class ViewExtractor:
    """Extracts view classes and identifies error handling issues"""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.api_root = self.project_root / "api"
        
        # Standard patterns we expect
        self.expected_patterns = {
            'imports': [
                'from api.common.mixins import BaseAPIView',
                'from api.common.decorators import log_api_call',
                'from api.common.services.base import ServiceException'
            ],
            'inheritance': ['BaseAPIView'],
            'method_decorator': 'log_api_call',
            'error_handling': 'handle_service_operation'
        }
    
    def find_view_files(self, app_name: str = None) -> List[Path]:
        """Find all views.py files"""
        view_files = []
        
        if app_name:
            app_path = self.api_root / app_name / "views.py"
            if app_path.exists():
                view_files.append(app_path)
        else:
            for app_dir in self.api_root.iterdir():
                if app_dir.is_dir() and not app_dir.name.startswith('__'):
                    views_file = app_dir / "views.py"
                    if views_file.exists():
                        view_files.append(views_file)
        
        return view_files
    
    def extract_file_content(self, file_path: Path) -> Tuple[str, ast.AST]:
        """Extract file content and parse AST"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            tree = ast.parse(content)
            return content, tree
        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            return None, None
    
    def identify_view_classes(self, tree: ast.AST, file_path: Path) -> List[Tuple[ast.ClassDef, int, int]]:
        """Identify all view classes in the file"""
        view_classes = []
        content_lines = None
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and self._is_view_class(node):
                # Calculate line range for the class
                if content_lines is None:
                    with open(file_path, 'r') as f:
                        content_lines = f.readlines()
                
                line_start = node.lineno
                line_end = self._find_class_end_line(node, content_lines)
                
                view_classes.append((node, line_start, line_end))
        
        return view_classes
    
    def _is_view_class(self, node: ast.ClassDef) -> bool:
        """Check if the class is a Django view"""
        view_indicators = [
            'View', 'APIView', 'GenericAPIView', 'ViewSet', 
            'ModelViewSet', 'ReadOnlyModelViewSet'
        ]
        
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id in view_indicators:
                return True
            elif isinstance(base, ast.Attribute) and base.attr in view_indicators:
                return True
        
        return False
    
    def _find_class_end_line(self, class_node: ast.ClassDef, content_lines: List[str]) -> int:
        """Find the end line of a class definition"""
        # Start from the class line and find the next class or end of file
        start_line = class_node.lineno - 1  # Convert to 0-based indexing
        indent_level = len(content_lines[start_line]) - len(content_lines[start_line].lstrip())
        
        for i in range(start_line + 1, len(content_lines)):
            line = content_lines[i]
            if line.strip():  # Non-empty line
                current_indent = len(line) - len(line.lstrip())
                # If we hit a line with same or less indentation, we've reached the end
                if current_indent <= indent_level and not line.strip().startswith(('@', 'class ', 'def ')):
                    return i
                # If we hit another class definition at the same level
                if line.strip().startswith('class ') and current_indent == indent_level:
                    return i
        
        return len(content_lines)
    
    def analyze_view_class(self, class_node: ast.ClassDef, file_path: Path, 
                          line_start: int, line_end: int) -> ViewClass:
        """Analyze a view class and identify issues"""
        app_name = file_path.parent.name
        
        # Extract class information - improved inheritance extraction
        inheritance = []
        for base in class_node.bases:
            if isinstance(base, ast.Name):
                inheritance.append(base.id)
            elif isinstance(base, ast.Attribute):
                if hasattr(base.value, 'id'):
                    inheritance.append(f"{base.value.id}.{base.attr}")
                else:
                    inheritance.append(base.attr)
            else:
                inheritance.append(str(base))
        
        methods = [node.name for node in class_node.body if isinstance(node, ast.FunctionDef)]
        
        # Get class decorators
        decorators = [self._get_decorator_name(d) for d in class_node.decorator_list]
        
        # Extract source code
        with open(file_path, 'r') as f:
            lines = f.readlines()
        source_code = ''.join(lines[line_start-1:line_end])
        
        # Identify issues
        issues = self._identify_class_issues(class_node, app_name, str(file_path))
        
        # Determine required imports
        imports_needed = self._determine_missing_imports(file_path)
        
        return ViewClass(
            app_name=app_name,
            file_path=str(file_path),
            class_name=class_node.name,
            line_start=line_start,
            line_end=line_end,
            source_code=source_code,
            imports_needed=imports_needed,
            inheritance=inheritance,
            methods=methods,
            decorators=decorators,
            issues=issues
        )
    
    def _identify_class_issues(self, class_node: ast.ClassDef, app_name: str, file_path: str) -> List[ViewIssue]:
        """Identify all issues in a view class"""
        issues = []
        
        # Check class-level issues - improved inheritance detection
        has_base_api_view = False
        
        # More accurate BaseAPIView detection
        for base in class_node.bases:
            if isinstance(base, ast.Name) and base.id == 'BaseAPIView':
                has_base_api_view = True
                break
            elif isinstance(base, ast.Attribute) and base.attr == 'BaseAPIView':
                has_base_api_view = True
                break
        
        if not has_base_api_view:
            # Create current pattern string more accurately
            current_bases = []
            for base in class_node.bases:
                if isinstance(base, ast.Name):
                    current_bases.append(base.id)
                elif isinstance(base, ast.Attribute):
                    if hasattr(base.value, 'id'):
                        current_bases.append(f"{base.value.id}.{base.attr}")
                    else:
                        current_bases.append(base.attr)
                else:
                    current_bases.append(str(base))
            
            current_pattern = f"class {class_node.name}({', '.join(current_bases)})"
            
            issues.append(ViewIssue(
                app_name=app_name,
                file_path=file_path,
                view_name=class_node.name,
                method_name="class",
                line_number=class_node.lineno,
                issue_type="missing_inheritance",
                severity="high",
                description="Class does not inherit from BaseAPIView",
                current_pattern=current_pattern,
                suggested_pattern=f"class {class_node.name}(GenericAPIView, BaseAPIView)"
            ))
        
        # Check method-level issues
        for method_node in class_node.body:
            if isinstance(method_node, ast.FunctionDef) and self._is_api_method(method_node):
                method_issues = self._analyze_method_issues(
                    method_node, class_node.name, app_name, file_path
                )
                issues.extend(method_issues)
        
        return issues
    
    def _analyze_method_issues(self, method_node: ast.FunctionDef, view_name: str, 
                              app_name: str, file_path: str) -> List[ViewIssue]:
        """Analyze issues in a specific method"""
        issues = []
        
        # Check for @log_api_call decorator
        has_log_api_call = any(
            (isinstance(d, ast.Name) and d.id == 'log_api_call') or
            (isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id == 'log_api_call')
            for d in method_node.decorator_list
        )
        
        if not has_log_api_call:
            issues.append(ViewIssue(
                app_name=app_name,
                file_path=file_path,
                view_name=view_name,
                method_name=method_node.name,
                line_number=method_node.lineno,
                issue_type="missing_decorator",
                severity="medium",
                description=f"Method {method_node.name} missing @log_api_call() decorator",
                current_pattern=f"def {method_node.name}(self, request)",
                suggested_pattern=f"@log_api_call()\n    def {method_node.name}(self, request)"
            ))
        
        # Check error handling pattern - improved detection
        has_handle_service_operation = False
        has_try_catch = False
        error_pattern = "none"
        
        # Walk through the method body to find patterns
        for node in ast.walk(method_node):
            if isinstance(node, ast.Call):
                # Check for handle_service_operation call
                if (isinstance(node.func, ast.Attribute) and 
                    node.func.attr == 'handle_service_operation'):
                    has_handle_service_operation = True
                    error_pattern = "handle_service_operation"
                    break
            elif isinstance(node, ast.Try):
                # Only count try blocks that are direct children of the method, not nested
                if node in method_node.body:
                    has_try_catch = True
                    if error_pattern == "none":
                        error_pattern = "try_catch"
        
        # Determine error handling issues
        if not has_handle_service_operation:
            severity = "critical" if has_try_catch else "high"
            description = ("Method uses try/catch instead of handle_service_operation pattern" 
                          if has_try_catch else 
                          "Method lacks proper error handling")
            
            issues.append(ViewIssue(
                app_name=app_name,
                file_path=file_path,
                view_name=view_name,
                method_name=method_node.name,
                line_number=method_node.lineno,
                issue_type="incorrect_error_handling",
                severity=severity,
                description=description,
                current_pattern=error_pattern,
                suggested_pattern="handle_service_operation",
                context={
                    "has_try_catch": has_try_catch,
                    "current_error_pattern": error_pattern
                }
            ))
        
        return issues
    
    def _is_api_method(self, node: ast.FunctionDef) -> bool:
        """Check if method is an API endpoint method"""
        api_methods = ['get', 'post', 'put', 'patch', 'delete']
        return node.name in api_methods
    
    def _get_decorator_name(self, decorator) -> str:
        """Extract decorator name from AST node"""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
            return decorator.func.id
        else:
            return str(decorator)
    
    def _determine_missing_imports(self, file_path: Path) -> List[str]:
        """Determine what imports are missing from the file"""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            missing_imports = []
            
            # Check for BaseAPIView import
            if 'from api.common.mixins import BaseAPIView' not in content and 'BaseAPIView' not in content:
                missing_imports.append('from api.common.mixins import BaseAPIView')
            
            # Check for log_api_call import
            if 'from api.common.decorators import log_api_call' not in content and 'log_api_call' not in content:
                missing_imports.append('from api.common.decorators import log_api_call')
            
            # Check for ServiceException import
            if 'from api.common.services.base import ServiceException' not in content and 'ServiceException' not in content:
                missing_imports.append('from api.common.services.base import ServiceException')
            
            return missing_imports
            
        except Exception as e:
            logger.error(f"Error checking imports in {file_path}: {e}")
            return []
    
    def print_analysis_report(self, view_classes: List[ViewClass], severity_filter: str = None):
        """Print analysis report with view classes that have issues"""
        if not view_classes:
            logger.info("No view classes found to analyze")
            return
        
        # Filter by severity if specified
        if severity_filter:
            filtered_classes = []
            for vc in view_classes:
                filtered_issues = [i for i in vc.issues if i.severity == severity_filter]
                if filtered_issues:
                    vc.issues = filtered_issues
                    filtered_classes.append(vc)
            view_classes = filtered_classes
        
        # Filter out classes with no issues
        problematic_classes = [vc for vc in view_classes if vc.issues]
        
        if not problematic_classes:
            print("✅ No issues found in the analyzed view classes!")
            return
        
        print("\n" + "="*100)
        print("VIEW CLASS EXTRACTION AND ISSUE ANALYSIS REPORT")
        print("="*100)
        
        # Group by severity
        severity_groups = {}
        for vc in problematic_classes:
            for issue in vc.issues:
                if issue.severity not in severity_groups:
                    severity_groups[issue.severity] = []
                severity_groups[issue.severity].append((vc, issue))
        
        # Display by severity
        severity_order = ['critical', 'high', 'medium', 'low']
        
        for severity in severity_order:
            if severity not in severity_groups:
                continue
            
            items = severity_groups[severity]
            print(f"\n🚨 {severity.upper()} PRIORITY ISSUES ({len(items)} items)")
            print("-" * 80)
            
            # Group by view class
            class_groups = {}
            for vc, issue in items:
                key = f"{vc.app_name}/{vc.class_name}"
                if key not in class_groups:
                    class_groups[key] = {'view_class': vc, 'issues': []}
                class_groups[key]['issues'].append(issue)
            
            for class_key, data in class_groups.items():
                vc = data['view_class']
                issues = data['issues']
                
                print(f"\n📋 {class_key}")
                print(f"   📁 File: {vc.file_path}:{vc.line_start}-{vc.line_end}")
                print(f"   🏗️  Inheritance: {' -> '.join(vc.inheritance)}")
                print(f"   🔧 Methods: {', '.join(vc.methods)}")
                
                if vc.imports_needed:
                    print(f"   📦 Missing Imports:")
                    for imp in vc.imports_needed:
                        print(f"      • {imp}")
                
                print(f"   ⚠️  Issues Found:")
                for issue in issues:
                    print(f"      • {issue.method_name}: {issue.description}")
                    print(f"        Current: {issue.current_pattern}")
                    print(f"        Suggested: {issue.suggested_pattern}")
                
                print()
        
        # Summary
        total_classes = len(problematic_classes)
        total_issues = sum(len(vc.issues) for vc in problematic_classes)
        
        # Count by issue type for better insights
        issue_type_counts = {}
        for vc in problematic_classes:
            for issue in vc.issues:
                issue_type = issue.issue_type
                if issue_type not in issue_type_counts:
                    issue_type_counts[issue_type] = 0
                issue_type_counts[issue_type] += 1
        
        print("\n" + "="*100)
        print("EXTRACTION SUMMARY")
        print("="*100)
        print(f"📊 View classes with issues: {total_classes}")
        print(f"🐛 Total issues found: {total_issues}")
        print(f"🔧 Classes ready for manual fixing: {total_classes}")
        
        if issue_type_counts:
            print(f"\n📈 Issue Type Breakdown:")
            for issue_type, count in sorted(issue_type_counts.items()):
                print(f"   • {issue_type.replace('_', ' ').title()}: {count}")
        
        print("\n💡 Use --extract --view <ViewName> to get the complete source code for manual fixing")
    
    def extract_view_for_fixing(self, view_class: ViewClass) -> str:
        """Extract view class in a format suitable for AI-assisted fixing"""
        output = []
        
        output.append("="*100)
        output.append(f"VIEW CLASS EXTRACTION FOR MANUAL FIXING")
        output.append("="*100)
        output.append(f"App: {view_class.app_name}")
        output.append(f"File: {view_class.file_path}")
        output.append(f"Class: {view_class.class_name}")
        output.append(f"Lines: {view_class.line_start}-{view_class.line_end}")
        output.append("")
        
        # Issues summary
        if view_class.issues:
            output.append("🚨 ISSUES IDENTIFIED:")
            for issue in view_class.issues:
                output.append(f"   • {issue.severity.upper()}: {issue.description}")
                output.append(f"     Method: {issue.method_name}")
                output.append(f"     Current: {issue.current_pattern}")
                output.append(f"     Suggested: {issue.suggested_pattern}")
            output.append("")
        
        # Required imports
        if view_class.imports_needed:
            output.append("📦 MISSING IMPORTS TO ADD:")
            for imp in view_class.imports_needed:
                output.append(f"   {imp}")
            output.append("")
        
        # Current source code
        output.append("📋 CURRENT SOURCE CODE:")
        output.append("-" * 80)
        output.append(view_class.source_code)
        output.append("-" * 80)
        output.append("")
        
        # Standard pattern reference
        output.append("✅ STANDARD PATTERN TO FOLLOW:")
        output.append(self._get_standard_pattern_example())
        output.append("")
        
        output.append("💡 NEXT STEPS:")
        output.append("   1. Review the issues identified above")
        output.append("   2. Add missing imports at the top of the file")
        output.append("   3. Update class inheritance to include BaseAPIView")
        output.append("   4. Add @log_api_call() decorators to API methods")
        output.append("   5. Replace try/catch with handle_service_operation pattern")
        output.append("   6. Test the updated view")
        
        return "\n".join(output)
    
    def _get_standard_pattern_example(self) -> str:
        """Get example of standard pattern"""
        return '''
class ExampleView(GenericAPIView, BaseAPIView):
    serializer_class = ExampleSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Example Endpoint",
        description="Example description"
    )
    @log_api_call()
    def post(self, request: Request) -> Response:
        """Example API method"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = ExampleService()
            result = service.do_something(
                user=request.user,
                data=serializer.validated_data
            )
            
            return result
        
        return self.handle_service_operation(
            operation,
            "Operation completed successfully",
            "Failed to complete operation"
        )
'''

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Extract view classes and identify error handling issues",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('--analyze', action='store_true',
                       help='Analyze view classes for issues')
    parser.add_argument('--extract', action='store_true',
                       help='Extract specific view class for fixing')
    parser.add_argument('--scan-all', action='store_true',
                       help='Scan all apps and show issues')
    parser.add_argument('--extract-issues', action='store_true',
                       help='Extract all problematic view classes from an app')
    parser.add_argument('--app', type=str,
                       help='Target app name')
    parser.add_argument('--view', type=str,
                       help='Target view class name')
    parser.add_argument('--severity', type=str, choices=['critical', 'high', 'medium', 'low'],
                       help='Filter by issue severity')
    parser.add_argument('--project-root', type=str,
                       help='Project root directory')
    
    args = parser.parse_args()
    
    if not any([args.analyze, args.extract, args.scan_all, args.extract_issues]):
        parser.error("Must specify one of: --analyze, --extract, --scan-all, --extract-issues")
    
    if args.extract and not (args.app and args.view):
        parser.error("--extract requires both --app and --view")
    
    # Initialize extractor
    extractor = ViewExtractor(args.project_root)
    
    # Find target files
    if args.scan_all:
        view_files = extractor.find_view_files()
    elif args.app:
        view_files = extractor.find_view_files(args.app)
    else:
        parser.error("Must specify --app or use --scan-all")
    
    if not view_files:
        logger.error(f"No view files found")
        sys.exit(1)
    
    # Process files
    all_view_classes = []
    
    for file_path in view_files:
        logger.info(f"Processing {file_path}")
        
        content, tree = extractor.extract_file_content(file_path)
        if not tree:
            continue
        
        view_classes_in_file = extractor.identify_view_classes(tree, file_path)
        
        for class_node, line_start, line_end in view_classes_in_file:
            if args.view and args.view not in class_node.name:
                continue
            
            view_class = extractor.analyze_view_class(class_node, file_path, line_start, line_end)
            all_view_classes.append(view_class)
    
    # Execute requested action
    if args.extract:
        target_view = next((vc for vc in all_view_classes if vc.class_name == args.view), None)
        if target_view:
            print(extractor.extract_view_for_fixing(target_view))
        else:
            logger.error(f"View class {args.view} not found in {args.app}")
    
    elif args.extract_issues:
        problematic_views = [vc for vc in all_view_classes if vc.issues]
        for vc in problematic_views:
            print(extractor.extract_view_for_fixing(vc))
            print("\n" + "="*100 + "\n")
    
    else:  # analyze or scan-all
        extractor.print_analysis_report(all_view_classes, args.severity)

if __name__ == "__main__":
    main()