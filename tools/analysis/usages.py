#!/usr/bin/env python3
"""
Django Project Usage Analyzer - Enhanced Core Logic

Contains robust functionality for analyzing Django project files and finding usages
of classes, methods, and other code elements across the entire codebase.

Author: ChargeGhar Development Team
"""

import ast
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class CodeElement:
    """Represents a code element (class, method, etc.)"""
    name: str
    type: str  # 'class', 'method', 'function', 'import', 'variable'
    location: str
    context: Optional[str] = None
    parent_class: Optional[str] = None


@dataclass
class UsageLocation:
    """Represents a usage location of a code element"""
    file: str
    line: int
    column: int
    context: str
    element_type: str
    usage_type: str


class UsageAnalyzer:
    """Enhanced analyzer for finding code usages and relationships."""

    def __init__(self, base_dir: str = "api"):
        self.script_dir = Path(__file__).resolve().parent
        self.project_root = self._find_project_root()
        self.base_dir = self._find_api_dir(base_dir)
        self.file_cache = {}  # Cache parsed files
        self.import_cache = defaultdict(set)  # Track imports per file

    def _find_project_root(self) -> Path:
        """Find the project root by looking for common Django project markers."""
        current = Path.cwd()
        
        # Check current directory and parents for Django project indicators
        for path in [current] + list(current.parents):
            # Look for manage.py, settings.py, or common Django structure
            if (path / 'manage.py').exists():
                return path
            if (path / 'api').exists() and (path / 'api').is_dir():
                return path
            if any((path / dirname).exists() for dirname in ['config', 'core', 'settings']):
                return path
        
        # If not found, try the script directory
        if (self.script_dir.parent / 'manage.py').exists():
            return self.script_dir.parent
        
        # Default to current working directory
        return current

    def _find_api_dir(self, base_dir_name: str) -> Path:
        """Find the API/apps directory flexibly."""
        # Try multiple possible locations
        possible_paths = [
            self.project_root / base_dir_name,  # <project_root>/api
            self.project_root / 'apps',  # <project_root>/apps
            self.project_root / 'src' / base_dir_name,  # <project_root>/src/api
            self.project_root,  # Apps directly in project root
            Path.cwd() / base_dir_name,  # Current dir / api
            self.script_dir.parent / base_dir_name,  # Script parent / api
        ]
        
        for path in possible_paths:
            if path.exists() and path.is_dir():
                # Check if it contains Python files or subdirectories
                if any(path.glob("*.py")) or any(p.is_dir() for p in path.iterdir() if not p.name.startswith('_')):
                    return path
        
        # If nothing found, return the first option as default
        return self.project_root / base_dir_name

    def analyze_file(self, app_name: str, file_name: str) -> Dict[str, Any]:
        """Analyze a specific file to extract classes, methods, and imports."""
        file_path = self.base_dir / app_name / file_name
        cache_key = str(file_path)

        # Return cached result if available
        if cache_key in self.file_cache:
            return self.file_cache[cache_key]

        if not file_path.exists():
            return {'error': 'File not found'}

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()

            tree = ast.parse(source_code)

            analysis = {
                'app': app_name,
                'file': file_name,
                'file_path': str(file_path),
                'classes': [],
                'methods': [],
                'functions': [],
                'imports': [],
                'variables': [],
                'constants': [],
                'source_lines': source_code.splitlines()
            }

            # Analyze imports first
            analysis['imports'] = self._extract_imports(tree)
            
            # Build import map for this file
            self.import_cache[cache_key] = {
                imp.get('alias') or imp.get('module', '').split('.')[-1] 
                for imp in analysis['imports']
            }

            # Analyze classes, methods, functions, and variables
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_info = self._analyze_class(node, source_code.splitlines())
                    analysis['classes'].append(class_info)

                elif isinstance(node, ast.FunctionDef):
                    # Check if it's a top-level function
                    if self._is_top_level_function(node, tree):
                        func_info = self._analyze_function(node)
                        analysis['functions'].append(func_info)

                elif isinstance(node, ast.Assign):
                    # Analyze module-level variables and constants
                    var_info = self._analyze_variable(node, tree)
                    if var_info:
                        if var_info['name'].isupper():
                            analysis['constants'].append(var_info)
                        else:
                            analysis['variables'].append(var_info)

            # Cache the result
            self.file_cache[cache_key] = analysis
            return analysis

        except SyntaxError as e:
            return {
                'app': app_name,
                'file': file_name,
                'error': f'Syntax error: {str(e)}'
            }
        except Exception as e:
            return {
                'app': app_name,
                'file': file_name,
                'error': f'Parse error: {str(e)}'
            }

    def find_usages(self, app_name: str, file_name: str, target: str) -> List[Dict[str, Any]]:
        """Find all usages of a specific class, method, or element across the project."""
        usages = []

        # Analyze the target file
        target_analysis = self.analyze_file(app_name, file_name)
        if not target_analysis or 'error' in target_analysis:
            return usages

        # Find the target element
        target_element = self._find_element_in_analysis(target_analysis, target)
        if not target_element:
            # Try partial matching for methods with class context
            target_element = self._find_element_partial(target_analysis, target)
            if not target_element:
                return usages

        print(f"🎯 Target found: {target_element.type} '{target_element.name}'")
        if target_element.parent_class:
            print(f"   Parent class: {target_element.parent_class}")

        # Search across entire project
        usages = self._search_project_wide(app_name, file_name, target, target_element)

        # Deduplicate usages
        usages = self._deduplicate_usages(usages)

        # Sort by file and line number
        usages.sort(key=lambda x: (x.get('file', ''), x.get('line', 0)))

        return usages

    def _extract_imports(self, tree: ast.AST) -> List[Dict[str, str]]:
        """Extract import statements from the AST with enhanced tracking."""
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        'module': alias.name,
                        'alias': alias.asname if alias.asname else alias.name.split('.')[-1],
                        'type': 'import',
                        'line': node.lineno,
                        'full_name': alias.name
                    })

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    imports.append({
                        'module': f"{module}.{alias.name}" if module else alias.name,
                        'alias': alias.asname if alias.asname else alias.name,
                        'type': 'from_import',
                        'line': node.lineno,
                        'from_module': module,
                        'imported_name': alias.name
                    })

        return imports

    def _analyze_class(self, node: ast.ClassDef, source_lines: List[str]) -> Dict[str, Any]:
        """Analyze a class definition with enhanced detail."""
        class_info = {
            'name': node.name,
            'type': 'class',
            'base_classes': [self._get_node_name(base) for base in node.bases],
            'methods': [],
            'class_variables': [],
            'line_number': node.lineno,
            'end_line': node.end_lineno if hasattr(node, 'end_lineno') else node.lineno,
            'docstring': ast.get_docstring(node),
            'decorators': [self._get_node_name(dec) for dec in node.decorator_list]
        }

        # Extract methods and class variables
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                method_info = {
                    'name': item.name,
                    'args': [arg.arg for arg in item.args.args],
                    'line_number': item.lineno,
                    'type': 'method',
                    'decorators': [self._get_node_name(dec) for dec in item.decorator_list],
                    'is_static': any(self._get_node_name(dec) == 'staticmethod' for dec in item.decorator_list),
                    'is_class_method': any(self._get_node_name(dec) == 'classmethod' for dec in item.decorator_list),
                    'is_property': any(self._get_node_name(dec) == 'property' for dec in item.decorator_list)
                }
                class_info['methods'].append(method_info)
            
            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        class_info['class_variables'].append({
                            'name': target.id,
                            'line': item.lineno
                        })

        return class_info

    def _analyze_function(self, node: ast.FunctionDef) -> Dict[str, Any]:
        """Analyze a function definition."""
        return {
            'name': node.name,
            'type': 'function',
            'args': [arg.arg for arg in node.args.args],
            'line_number': node.lineno,
            'decorators': [self._get_node_name(dec) for dec in node.decorator_list],
            'docstring': ast.get_docstring(node),
            'returns': self._get_node_name(node.returns) if node.returns else None
        }

    def _analyze_variable(self, node: ast.Assign, tree: ast.AST) -> Optional[Dict[str, Any]]:
        """Analyze a variable assignment at module level."""
        # Check if it's a module-level assignment
        for target in node.targets:
            if isinstance(target, ast.Name):
                return {
                    'name': target.id,
                    'type': 'variable',
                    'line_number': node.lineno
                }
        return None

    def _is_top_level_function(self, func_node: ast.FunctionDef, tree: ast.AST) -> bool:
        """Check if a function is defined at module level (not inside a class)."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if item == func_node:
                        return False
        return True

    def _get_node_name(self, node: ast.AST) -> str:
        """Get the name from an AST node."""
        if node is None:
            return ''
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            value = self._get_node_name(node.value)
            return f"{value}.{node.attr}" if value else node.attr
        elif isinstance(node, ast.Constant):
            return str(node.value)
        return str(type(node).__name__)

    def _find_element_in_analysis(self, analysis: Dict[str, Any], target: str) -> Optional[CodeElement]:
        """Find a specific element in the file analysis."""
        # Search in classes
        for cls in analysis.get('classes', []):
            if cls['name'] == target:
                return CodeElement(
                    name=target,
                    type='class',
                    location=f"{analysis['app']}/{analysis['file']}:{cls['line_number']}"
                )

            # Search in class methods
            for method in cls.get('methods', []):
                if method['name'] == target:
                    return CodeElement(
                        name=target,
                        type='method',
                        location=f"{analysis['app']}/{analysis['file']}:{method['line_number']}",
                        context=f"{cls['name']}.{method['name']}",
                        parent_class=cls['name']
                    )

        # Search in standalone functions
        for func in analysis.get('functions', []):
            if func['name'] == target:
                return CodeElement(
                    name=target,
                    type='function',
                    location=f"{analysis['app']}/{analysis['file']}:{func['line_number']}"
                )

        # Search in variables and constants
        for var in analysis.get('variables', []) + analysis.get('constants', []):
            if var['name'] == target:
                return CodeElement(
                    name=target,
                    type='variable',
                    location=f"{analysis['app']}/{analysis['file']}:{var['line_number']}"
                )

        return None

    def _find_element_partial(self, analysis: Dict[str, Any], target: str) -> Optional[CodeElement]:
        """Find element with partial matching (e.g., ClassName.method_name)."""
        if '.' in target:
            class_name, method_name = target.split('.', 1)
            for cls in analysis.get('classes', []):
                if cls['name'] == class_name:
                    for method in cls.get('methods', []):
                        if method['name'] == method_name:
                            return CodeElement(
                                name=method_name,
                                type='method',
                                location=f"{analysis['app']}/{analysis['file']}:{method['line_number']}",
                                context=f"{class_name}.{method_name}",
                                parent_class=class_name
                            )
        return None

    def _search_project_wide(self, source_app: str, source_file: str, target: str, 
                            target_element: CodeElement) -> List[Dict[str, Any]]:
        """Search for usages across the entire project with improved detection."""
        usages = []
        search_paths = [self.base_dir]

        # Also search in project root for settings, urls, etc.
        if self.project_root.exists() and self.project_root != self.base_dir:
            search_paths.append(self.project_root)

        print(f"🔎 Searching in:")
        for path in search_paths:
            print(f"   • {path}")

        files_searched = 0
        for search_path in search_paths:
            for root, dirs, files in os.walk(search_path):
                # Skip common directories
                dirs[:] = [d for d in dirs if not d.startswith('__') 
                          and d not in ['migrations', 'node_modules', '.git', 'venv', 'env', '.venv', 
                                       'staticfiles', 'media', '__pycache__', '.pytest_cache', 
                                       'htmlcov', 'dist', 'build', '.tox']]

                for file in files:
                    if file.endswith('.py') and not file.startswith('__'):
                        file_path = Path(root) / file
                        
                        # Skip the source file
                        try:
                            rel_path = file_path.relative_to(self.base_dir)
                            if str(rel_path) == f"{source_app}/{source_file}":
                                continue
                        except ValueError:
                            pass

                        try:
                            files_searched += 1
                            file_usages = self._search_in_file(file_path, target, target_element)
                            if file_usages:
                                usages.extend(file_usages)
                                print(f"✓ Found {len(file_usages)} usage(s) in {file_path.relative_to(self.project_root)}")
                        except Exception as e:
                            # Skip files that can't be parsed
                            continue

        print(f"📊 Searched {files_searched} files")
        return usages

    def _search_in_file(self, file_path: Path, target: str, 
                       target_element: CodeElement) -> List[Dict[str, Any]]:
        """Search for usages in a specific file with comprehensive pattern matching."""
        usages = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()

            # Use AST for more accurate detection
            try:
                tree = ast.parse(content)
                ast_usages = self._find_usages_ast(tree, file_path, lines, target, target_element)
                usages.extend(ast_usages)
            except:
                pass

            # Use regex for pattern matching (backup method)
            for line_num, line in enumerate(lines, 1):
                line_stripped = line.strip()
                if not line_stripped or line_stripped.startswith('#'):
                    continue

                if target_element.type == 'class':
                    usages.extend(self._find_class_usage(line, line_num, file_path, target))
                elif target_element.type in ['method', 'function']:
                    usages.extend(self._find_method_usage(line, line_num, file_path, target, target_element))
                elif target_element.type == 'variable':
                    usages.extend(self._find_variable_usage(line, line_num, file_path, target))

        except Exception as e:
            pass

        return usages

    def _find_usages_ast(self, tree: ast.AST, file_path: Path, lines: List[str],
                        target: str, target_element: CodeElement) -> List[Dict[str, Any]]:
        """Find usages using AST analysis for accuracy."""
        usages = []

        for node in ast.walk(tree):
            # Class instantiation
            if isinstance(node, ast.Call):
                func_name = self._get_node_name(node.func)
                
                # Direct function/class call
                if target in func_name:
                    context = lines[node.lineno - 1].strip() if node.lineno <= len(lines) else ''
                    
                    # Determine usage type
                    usage_type = 'call'
                    if '.delay' in context:
                        usage_type = 'celery_delay'
                    elif '.apply_async' in context:
                        usage_type = 'celery_apply_async'
                    elif '.s(' in context or '.si(' in context:
                        usage_type = 'celery_signature'
                    elif target_element.type == 'class':
                        usage_type = 'instantiation'
                    elif target_element.type in ['method', 'function']:
                        usage_type = 'function_call'
                    
                    usages.append({
                        'file': str(file_path.relative_to(self.project_root)),
                        'line': node.lineno,
                        'type': usage_type,
                        'context': context,
                        'element': target
                    })

            # Attribute access (method calls, including Celery methods)
            elif isinstance(node, ast.Attribute):
                if node.attr == target:
                    context = lines[node.lineno - 1].strip() if node.lineno <= len(lines) else ''
                    usages.append({
                        'file': str(file_path.relative_to(self.project_root)),
                        'line': node.lineno,
                        'type': 'attribute_access',
                        'context': context,
                        'element': target
                    })
                # Check for Celery task patterns like task_name.delay
                elif isinstance(node.value, ast.Name) and node.value.id == target:
                    if node.attr in ['delay', 'apply_async', 's', 'si', 'apply']:
                        context = lines[node.lineno - 1].strip() if node.lineno <= len(lines) else ''
                        usages.append({
                            'file': str(file_path.relative_to(self.project_root)),
                            'line': node.lineno,
                            'type': f'celery_{node.attr}',
                            'context': context,
                            'element': target
                        })

            # Name references (variable usage, function references)
            elif isinstance(node, ast.Name) and node.id == target:
                context = lines[node.lineno - 1].strip() if node.lineno <= len(lines) else ''
                # Skip if it's a definition
                if not (context.startswith('def ') or context.startswith('class ')):
                    usages.append({
                        'file': str(file_path.relative_to(self.project_root)),
                        'line': node.lineno,
                        'type': 'reference',
                        'context': context,
                        'element': target
                    })

            # Import statements
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if target in alias.name or (alias.asname and target == alias.asname):
                            usages.append({
                                'file': str(file_path.relative_to(self.project_root)),
                                'line': node.lineno,
                                'type': 'import',
                                'context': lines[node.lineno - 1].strip() if node.lineno <= len(lines) else '',
                                'element': target
                            })
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        if target == alias.name or (alias.asname and target == alias.asname):
                            usages.append({
                                'file': str(file_path.relative_to(self.project_root)),
                                'line': node.lineno,
                                'type': 'import',
                                'context': lines[node.lineno - 1].strip() if node.lineno <= len(lines) else '',
                                'element': target
                            })

        return usages

    def _find_class_usage(self, line: str, line_num: int, file_path: Path, 
                         class_name: str) -> List[Dict[str, Any]]:
        """Find usages of a class with comprehensive patterns."""
        usages = []
        
        # Skip comments
        if line.strip().startswith('#'):
            return usages

        patterns = [
            (rf'\b{class_name}\s*\(', 'instantiation'),  # ClassName()
            (rf'class\s+\w+\([^)]*\b{class_name}\b', 'inheritance'),  # class X(ClassName)
            (rf':\s*{class_name}\b', 'type_annotation'),  # var: ClassName
            (rf'->\s*{class_name}\b', 'return_type'),  # -> ClassName
            (rf'isinstance\([^,]+,\s*{class_name}\b', 'isinstance_check'),  # isinstance(x, ClassName)
            (rf'issubclass\([^,]+,\s*{class_name}\b', 'issubclass_check'),  # issubclass(x, ClassName)
            (rf'\b{class_name}\s*=', 'assignment'),  # var = ClassName
            (rf'import.*\b{class_name}\b', 'import'),  # import ClassName
        ]

        for pattern, usage_type in patterns:
            if re.search(pattern, line):
                usages.append({
                    'file': str(file_path.relative_to(self.project_root)),
                    'line': line_num,
                    'type': usage_type,
                    'context': line.strip(),
                    'element': class_name
                })

        return usages

    def _find_method_usage(self, line: str, line_num: int, file_path: Path, 
                          method_name: str, target_element: CodeElement) -> List[Dict[str, Any]]:
        """Find usages of a method with context awareness."""
        usages = []
        
        if line.strip().startswith('#'):
            return usages

        # Method call patterns
        patterns = [
            (rf'\.{method_name}\s*\(', 'method_call'),  # .method_name()
            (rf'\b{method_name}\s*\(', 'function_call'),  # method_name()
            (rf'@{method_name}\b', 'decorator'),  # @method_name
            # Celery task patterns
            (rf'\b{method_name}\.delay\s*\(', 'celery_delay'),  # task_name.delay()
            (rf'\b{method_name}\.apply_async\s*\(', 'celery_apply_async'),  # task_name.apply_async()
            (rf'\b{method_name}\.s\s*\(', 'celery_signature'),  # task_name.s()
            (rf'\b{method_name}\.si\s*\(', 'celery_immutable'),  # task_name.si()
            # Django management command patterns
            (rf'call_command\s*\(\s*["\'].*{method_name}', 'management_command'),
            # URL patterns
            (rf'path\s*\([^,]*,\s*{method_name}', 'url_pattern'),
            (rf'url\s*\([^,]*,\s*{method_name}', 'url_pattern'),
            # Signal connections
            (rf'\.connect\s*\(\s*{method_name}', 'signal_connection'),
            (rf'@receiver\s*\([^)]*\)\s*\n\s*def\s+{method_name}', 'signal_receiver'),
        ]

        for pattern, usage_type in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                usages.append({
                    'file': str(file_path.relative_to(self.project_root)),
                    'line': line_num,
                    'type': usage_type,
                    'context': line.strip(),
                    'element': method_name
                })

        return usages

    def _find_variable_usage(self, line: str, line_num: int, file_path: Path, 
                           var_name: str) -> List[Dict[str, Any]]:
        """Find usages of a variable or function name."""
        usages = []
        
        if line.strip().startswith('#'):
            return usages

        # Check for the name as a word boundary (not part of another word)
        if re.search(rf'\b{var_name}\b', line):
            # Skip if it's the definition line
            if not (line.strip().startswith(f'def {var_name}') or 
                   line.strip().startswith(f'class {var_name}') or
                   line.strip().startswith(f'{var_name} =')):
                
                # Determine usage type
                usage_type = 'variable_usage'
                if '.delay(' in line:
                    usage_type = 'celery_delay'
                elif '.apply_async(' in line:
                    usage_type = 'celery_apply_async'
                elif f'{var_name}(' in line:
                    usage_type = 'function_call'
                elif f'"{var_name}"' in line or f"'{var_name}'" in line:
                    usage_type = 'string_reference'
                
                usages.append({
                    'file': str(file_path.relative_to(self.project_root)),
                    'line': line_num,
                    'type': usage_type,
                    'context': line.strip(),
                    'element': var_name
                })

        # Also check for string references (common for Celery task names)
        # Match patterns like: send_task('app.tasks.task_name')
        string_patterns = [
            rf'["\'].*\.{var_name}["\']',  # 'users.tasks.cleanup_expired_audit_logs'
            rf'["\'].*{var_name}["\']',     # 'cleanup_expired_audit_logs'
        ]
        
        for pattern in string_patterns:
            if re.search(pattern, line):
                usages.append({
                    'file': str(file_path.relative_to(self.project_root)),
                    'line': line_num,
                    'type': 'string_reference',
                    'context': line.strip(),
                    'element': var_name
                })

        return usages

    def _deduplicate_usages(self, usages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate usage entries."""
        seen = set()
        unique_usages = []
        
        for usage in usages:
            key = (usage.get('file'), usage.get('line'), usage.get('type'))
            if key not in seen:
                seen.add(key)
                unique_usages.append(usage)
        
        return unique_usages

    def get_file_summary(self, app_name: str, file_name: str) -> Dict[str, Any]:
        """Get comprehensive summary of a file's structure."""
        analysis = self.analyze_file(app_name, file_name)

        if not analysis or 'error' in analysis:
            return {'error': analysis.get('error', 'Unknown error') if analysis else 'File not found'}

        summary = {
            'file_path': f"{app_name}/{file_name}",
            'total_lines': len(analysis.get('source_lines', [])),
            'classes_count': len(analysis.get('classes', [])),
            'methods_count': sum(len(cls.get('methods', [])) for cls in analysis.get('classes', [])),
            'functions_count': len(analysis.get('functions', [])),
            'imports_count': len(analysis.get('imports', [])),
            'variables_count': len(analysis.get('variables', [])),
            'constants_count': len(analysis.get('constants', [])),
            'complexity_score': self._calculate_complexity(analysis)
        }

        return summary

    def _calculate_complexity(self, analysis: Dict[str, Any]) -> int:
        """Calculate complexity score for the file."""
        score = 0
        score += len(analysis.get('classes', [])) * 5
        score += sum(len(cls.get('methods', [])) for cls in analysis.get('classes', [])) * 2
        score += len(analysis.get('functions', [])) * 2
        score += len(analysis.get('imports', []))
        return score

    def find_dependencies(self, app_name: str, file_name: str) -> Dict[str, List[str]]:
        """Find all dependencies with categorization."""
        analysis = self.analyze_file(app_name, file_name)

        if not analysis or 'error' in analysis:
            return {}

        dependencies = {
            'internal': [],
            'external': [],
            'relative': [],
            'django': [],
            'third_party': []
        }

        for imp in analysis.get('imports', []):
            module = imp.get('module', '')

            if module.startswith('.'):
                dependencies['relative'].append(module)
            elif module.startswith('django') or module.startswith('rest_framework'):
                dependencies['django'].append(module)
            elif any(module.startswith(prefix) for prefix in ['api.', self.base_dir.name]):
                dependencies['internal'].append(module)
            else:
                dependencies['third_party'].append(module)

        return dependencies