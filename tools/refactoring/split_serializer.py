#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Serializer Splitter Tool
Intelligently splits Django serializers into categorized files and generates proper __init__.py
"""

import os
import re
import json
import ast
import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict


class SerializerAnalyzer:
    """Analyzes serializers to extract metadata and dependencies"""
    
    def __init__(self, serializer_file: str):
        self.serializer_file = serializer_file
        self.serializers = []
        self.imports = []
        self.global_code = []
        
    def analyze(self) -> Dict:
        """Analyze the serializer file and extract all serializers"""
        if not os.path.exists(self.serializer_file):
            raise FileNotFoundError(f"Serializer file not found: {self.serializer_file}")
        
        with open(self.serializer_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            print(f"Warning: Could not parse {self.serializer_file}: {e}")
            return self._fallback_analysis(content)
        
        return self._ast_analysis(tree, content)
    
    def _ast_analysis(self, tree: ast.AST, content: str) -> Dict:
        """Use AST to analyze serializers"""
        lines = content.split('\n')
        
        # Extract imports - only at module level
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                start_line = node.lineno - 1
                end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line
                import_text = '\n'.join(lines[start_line:end_line + 1]).strip()
                
                # Only add if it's a valid import line
                if import_text.startswith(('import ', 'from ')):
                    self.imports.append(import_text)
        
        # Extract serializer classes
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if it's a serializer
                is_serializer = False
                for base in node.bases:
                    base_name = self._get_name(base)
                    if 'Serializer' in base_name:
                        is_serializer = True
                        break
                
                if is_serializer:
                    start_line = node.lineno - 1
                    end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line
                    
                    # Get the complete class code including decorators
                    class_start = start_line
                    for dec in node.decorator_list:
                        if dec.lineno - 1 < class_start:
                            class_start = dec.lineno - 1
                    
                    class_code = '\n'.join(lines[class_start:end_line + 1])
                    
                    serializer_info = {
                        'name': node.name,
                        'code': class_code,
                        'line_start': class_start,
                        'line_end': end_line,
                        'bases': [self._get_name(base) for base in node.bases],
                        'category': self._categorize_serializer(node.name),
                        'dependencies': self._extract_dependencies(node, lines)
                    }
                    self.serializers.append(serializer_info)
        
        return {
            'imports': self.imports,
            'serializers': self.serializers,
            'total_count': len(self.serializers)
        }
    
    def _fallback_analysis(self, content: str) -> Dict:
        """Fallback regex-based analysis if AST fails"""
        lines = content.split('\n')
        
        # Extract imports (only lines starting with import or from at the beginning)
        for i, line in enumerate(lines):
            stripped = line.strip()
            # Must start with import/from and not be inside code blocks
            if stripped.startswith(('import ', 'from ')) and not line.startswith((' ', '\t')):
                # Validate it's a complete import statement
                if 'import' in stripped:
                    self.imports.append(stripped)
        
        # Extract serializer classes
        class_pattern = r'^class\s+(\w+)\s*\([^)]*Serializer[^)]*\)\s*:'
        
        i = 0
        while i < len(lines):
            match = re.match(class_pattern, lines[i].strip())
            if match:
                class_name = match.group(1)
                start_line = i
                
                # Find the end of the class
                indent_level = len(lines[i]) - len(lines[i].lstrip())
                end_line = i + 1
                
                while end_line < len(lines):
                    line = lines[end_line]
                    if line.strip() and not line.startswith(' ' * (indent_level + 1)):
                        if not line.strip().startswith('#'):
                            break
                    end_line += 1
                
                class_code = '\n'.join(lines[start_line:end_line])
                
                serializer_info = {
                    'name': class_name,
                    'code': class_code,
                    'line_start': start_line,
                    'line_end': end_line - 1,
                    'bases': ['Serializer'],
                    'category': self._categorize_serializer(class_name),
                    'dependencies': []
                }
                self.serializers.append(serializer_info)
                i = end_line
            else:
                i += 1
        
        return {
            'imports': self.imports,
            'serializers': self.serializers,
            'total_count': len(self.serializers)
        }
    
    def _get_name(self, node) -> str:
        """Get the name from an AST node"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return str(node)
    
    def _categorize_serializer(self, name: str) -> str:
        """Automatically categorize serializer based on name"""
        name_lower = name.lower()
        
        # Category keywords
        categories = {
            'user': ['user', 'profile', 'account', 'auth'],
            'station': ['station', 'location', 'charging'],
            'rental': ['rental', 'booking', 'reservation'],
            'payment': ['payment', 'transaction', 'wallet', 'refund'],
            'notification': ['notification', 'message', 'alert'],
            'analytics': ['analytics', 'report', 'stats', 'metric'],
            'content': ['content', 'media', 'image', 'file'],
            'amenity': ['amenity', 'facility', 'feature'],
            'admin': ['admin', 'management'],
            'kyc': ['kyc', 'verification', 'document'],
            'coupon': ['coupon', 'discount', 'promo'],
            'withdrawal': ['withdrawal', 'payout'],
        }
        
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in name_lower:
                    return category
        
        return 'common'
    
    def _extract_dependencies(self, node: ast.ClassDef, lines: List[str]) -> List[str]:
        """Extract serializer dependencies from the class"""
        dependencies = set()
        
        # Look for field definitions that reference other serializers
        for item in ast.walk(node):
            if isinstance(item, ast.Call):
                func_name = self._get_name(item.func)
                if 'Serializer' in func_name and func_name != node.name:
                    dependencies.add(func_name)
        
        return list(dependencies)


class ProposalGenerator:
    """Generates a proposal JSON for splitting serializers"""
    
    def __init__(self, analysis_result: Dict):
        self.analysis = analysis_result
        self.proposal = {
            'source_file': None,
            'categories': defaultdict(list),
            'metadata': {
                'total_serializers': analysis_result['total_count'],
                'split_strategy': 'category_based'
            }
        }
    
    def generate(self, output_file: str = 'proposal.json'):
        """Generate the proposal JSON"""
        # Group serializers by category
        for serializer in self.analysis['serializers']:
            category = serializer['category']
            self.proposal['categories'][category].append({
                'name': serializer['name'],
                'original_category': category,
                'suggested_file': f"{category}_serializers.py",
                'dependencies': serializer['dependencies'],
                'can_be_recategorized': True
            })
        
        # Convert defaultdict to regular dict for JSON serialization
        self.proposal['categories'] = dict(self.proposal['categories'])
        
        # Add additional metadata
        self.proposal['metadata']['categories_count'] = len(self.proposal['categories'])
        self.proposal['metadata']['instructions'] = (
            "Review and modify the 'suggested_file' for each serializer. "
            "You can group multiple categories into one file or split them further. "
            "After editing, run with 'execute' command."
        )
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.proposal, f, indent=2)
        
        print(f"✅ Proposal generated: {output_file}")
        print(f"📊 Found {self.proposal['metadata']['total_serializers']} serializers")
        print(f"📁 Suggested {self.proposal['metadata']['categories_count']} categories")
        print("\n📝 Categories:")
        for category, serializers in self.proposal['categories'].items():
            print(f"  - {category}: {len(serializers)} serializers")
        
        return output_file


class SerializerSplitter:
    """Executes the split based on proposal"""
    
    def __init__(self, app_path: str, proposal_file: str):
        self.app_path = Path(app_path)
        self.proposal_file = proposal_file
        self.serializers_dir = self.app_path / 'serializers'
        
    def execute(self):
        """Execute the split based on proposal"""
        # Load proposal
        with open(self.proposal_file, 'r', encoding='utf-8') as f:
            proposal = json.load(f)
        
        # Get original serializer file
        original_file = self.app_path / 'serializers.py'
        if not original_file.exists():
            raise FileNotFoundError(f"Original serializers.py not found in {self.app_path}")
        
        # Analyze the original file
        analyzer = SerializerAnalyzer(str(original_file))
        analysis = analyzer.analyze()
        
        # Create serializers directory
        self.serializers_dir.mkdir(exist_ok=True)
        
        # Group serializers by target file
        file_groups = defaultdict(list)
        serializer_map = {s['name']: s for s in analysis['serializers']}
        
        for category, serializers in proposal['categories'].items():
            for ser_info in serializers:
                target_file = ser_info['suggested_file']
                if ser_info['name'] in serializer_map:
                    file_groups[target_file].append(serializer_map[ser_info['name']])
        
        # Write split files
        created_files = []
        for filename, serializers in file_groups.items():
            filepath = self.serializers_dir / filename
            self._write_serializer_file(filepath, serializers, analysis['imports'])
            created_files.append(filename)
            print(f"✅ Created: {filepath}")
        
        # Generate __init__.py
        self._generate_init_file(file_groups)
        
        # Backup original file
        backup_file = self.app_path / 'serializers.py.backup'
        if not backup_file.exists():
            original_file.rename(backup_file)
            print(f"💾 Backed up original file to: {backup_file}")
        
        print(f"\n✨ Split complete! Created {len(created_files)} files in {self.serializers_dir}")
        
    def _write_serializer_file(self, filepath: Path, serializers: List[Dict], imports: List[str]):
        """Write a serializer file with necessary imports"""
        content_parts = []
        
        # Add header comment
        content_parts.append(f'"""')
        content_parts.append(f'{filepath.stem.replace("_", " ").title()}')
        content_parts.append(f'Auto-generated by split_serializer.py')
        content_parts.append(f'"""')
        content_parts.append('')
        
        # Add imports - clean and deduplicate
        unique_imports = self._clean_imports(imports)
        
        for imp in sorted(unique_imports):
            content_parts.append(imp)
        
        content_parts.append('')
        content_parts.append('')
        
        # Add serializer classes
        for serializer in serializers:
            content_parts.append(serializer['code'])
            content_parts.append('')
            content_parts.append('')
        
        # Write file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content_parts))
    
    def _clean_imports(self, imports: List[str]) -> Set[str]:
        """Clean and deduplicate imports"""
        unique_imports = set()
        
        for imp in imports:
            imp = imp.strip()
            
            # Skip empty lines
            if not imp:
                continue
            
            # Skip comments and non-import lines
            if not (imp.startswith('import ') or imp.startswith('from ')):
                continue
            
            # Skip lines that are clearly code (contain try:, if, return, etc.)
            skip_keywords = ['try:', 'except:', 'if ', 'return ', 'for ', 'while ', '=']
            if any(keyword in imp for keyword in skip_keywords):
                continue
            
            # Remove inline comments
            if '#' in imp:
                imp = imp.split('#')[0].strip()
            
            # Only add valid import statements
            if imp.startswith(('import ', 'from ')):
                unique_imports.add(imp)
        
        return unique_imports
    
    def _generate_init_file(self, file_groups: Dict[str, List[Dict]]):
        """Generate __init__.py with all exports"""
        init_file = self.serializers_dir / '__init__.py'
        
        content_parts = []
        content_parts.append('"""')
        content_parts.append('Serializers Package')
        content_parts.append('Auto-generated imports - DO NOT EDIT MANUALLY')
        content_parts.append('"""')
        content_parts.append('')
        
        # Collect all serializers by file
        all_exports = []
        
        for filename, serializers in sorted(file_groups.items()):
            module_name = filename.replace('.py', '')
            serializer_names = [s['name'] for s in serializers]
            
            content_parts.append(f'# From {filename}')
            content_parts.append(f'from .{module_name} import (')
            for name in sorted(serializer_names):
                content_parts.append(f'    {name},')
            content_parts.append(')')
            content_parts.append('')
            
            all_exports.extend(serializer_names)
        
        # Add __all__ for explicit exports
        content_parts.append('')
        content_parts.append('__all__ = [')
        for name in sorted(all_exports):
            content_parts.append(f'    "{name}",')
        content_parts.append(']')
        
        # Write file
        with open(init_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content_parts))
        
        print(f"✅ Generated: {init_file}")
        print(f"📦 Exported {len(all_exports)} serializers")


def main():
    parser = argparse.ArgumentParser(
        description='Split Django serializers into organized files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate proposal
  python split_serializer.py --app admin generate
  
  # Generate with custom output
  python split_serializer.py --app admin generate --output my_proposal.json
  
  # Execute split based on proposal
  python split_serializer.py --app admin execute proposal.json
  
  # Execute with custom proposal
  python split_serializer.py --app admin execute my_proposal.json
        """
    )
    
    parser.add_argument(
        '--app',
        required=True,
        help='Django app directory name (e.g., admin)'
    )
    
    parser.add_argument(
        'command',
        choices=['generate', 'execute', 'exec'],
        help='Command to run: generate (create proposal) or execute/exec (split files)'
    )
    
    parser.add_argument(
        'proposal_file',
        nargs='?',
        default='proposal.json',
        help='Proposal JSON file (default: proposal.json)'
    )
    
    parser.add_argument(
        '--output',
        '-o',
        help='Output file for proposal (only for generate command)'
    )
    
    args = parser.parse_args()
    
    # Normalize command
    if args.command == 'exec':
        args.command = 'execute'
    
    # Get app path
    app_path = Path(args.app)
    if not app_path.exists():
        print(f"❌ Error: App directory '{args.app}' not found")
        return 1
    
    serializer_file = app_path / 'serializers.py'
    
    try:
        if args.command == 'generate':
            # Generate proposal
            print(f"🔍 Analyzing {serializer_file}...")
            
            analyzer = SerializerAnalyzer(str(serializer_file))
            analysis = analyzer.analyze()
            
            output_file = args.output or args.proposal_file
            generator = ProposalGenerator(analysis)
            generator.generate(output_file)
            
            print(f"\n📝 Review and edit {output_file}, then run:")
            print(f"   python split_serializer.py --app {args.app} execute {output_file}")
            
        elif args.command == 'execute':
            # Execute split
            print(f"🚀 Executing split based on {args.proposal_file}...")
            
            splitter = SerializerSplitter(str(app_path), args.proposal_file)
            splitter.execute()
            
            print(f"\n✅ Done! Your serializers have been split.")
            print(f"💡 Original file backed up as serializers.py.backup")
            print(f"📦 Import serializers from: from {args.app}.serializers import YourSerializer")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())