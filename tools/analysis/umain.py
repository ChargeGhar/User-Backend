#!/usr/bin/env python3
"""
Django Project Usage Analyzer - Enhanced Main Entry Point

Provides a powerful CLI for analyzing Django project components, finding usages,
and exploring code relationships with detailed insights.

Usage:
    python ./tools/umain.py --list-apps
    python ./tools/umain.py --app users --list-files
    python ./tools/umain.py --app points --file tasks.py --list
    python ./tools/umain.py --app users --file services.py --usage UserService
    python ./tools/umain.py --app users --file services.py --usage UserService --verbose
    python ./tools/umain.py --app payments --file models.py --usage Transaction --export results.txt

Author: ChargeGhar Development Team
"""

import argparse
import sys
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from collections import defaultdict

from usages import UsageAnalyzer


class Colors:
    """Terminal color codes."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class UsageAnalyzerCLI:
    """Enhanced Command Line Interface for Usage Analyzer."""

    def __init__(self, colored: bool = True, base_dir: str = "api"):
        self.analyzer = UsageAnalyzer(base_dir)
        self.base_dir = self.analyzer.base_dir
        self.project_root = self.analyzer.project_root
        self.colored = colored
        
        # Print diagnostic info if base_dir doesn't exist
        if not self.base_dir.exists():
            print(f"⚠️  Warning: Directory '{self.base_dir}' not found")
            print(f"📍 Current working directory: {Path.cwd()}")
            print(f"📍 Script location: {Path(__file__).resolve().parent}")
            print(f"📍 Detected project root: {self.project_root}")
            print(f"📍 Looking for apps in: {self.base_dir}")
            print()

    def colorize(self, text: str, color: str) -> str:
        """Apply color to text if colors are enabled."""
        if self.colored:
            return f"{color}{text}{Colors.END}"
        return text

    def list_apps(self) -> List[str]:
        """List all available Django apps."""
        if not self.base_dir.exists():
            # Try to find apps in alternative locations
            alternative_paths = [
                self.project_root,
                self.project_root / 'apps',
                self.project_root / 'src',
                Path.cwd(),
            ]
            
            for alt_path in alternative_paths:
                if alt_path.exists():
                    apps = self._scan_for_apps(alt_path)
                    if apps:
                        print(f"💡 Found apps in: {alt_path}")
                        self.base_dir = alt_path
                        self.analyzer.base_dir = alt_path
                        return apps
            
            return []

        return self._scan_for_apps(self.base_dir)

    def _scan_for_apps(self, directory: Path) -> List[str]:
        """Scan a directory for Django apps."""
        apps = []
        
        try:
            for item in directory.iterdir():
                if item.is_dir() and not item.name.startswith('_') and not item.name.startswith('.'):
                    # Check if it looks like a Django app (has Python files or models.py)
                    if any(item.glob("*.py")) or (item / 'models.py').exists():
                        apps.append(item.name)
        except PermissionError:
            pass
        
        return sorted(apps)

    def list_app_files(self, app_name: str) -> List[str]:
        """List all Python files in a specific app."""
        app_path = self.base_dir / app_name
        if not app_path.exists():
            return []

        files = []
        for file_path in app_path.glob("*.py"):
            if file_path.is_file() and not file_path.name.startswith('__'):
                files.append(file_path.name)
        return sorted(files)

    def run_list_command(self, app_name: str, file_name: str, verbose: bool = False) -> int:
        """Run the list command to show classes and methods."""
        print(self.colorize(f"📋 Analyzing {app_name}/{file_name}...", Colors.CYAN))

        # Validate app and file
        if app_name not in self.list_apps():
            print(self.colorize(f"❌ App '{app_name}' not found!", Colors.RED))
            print(f"\n💡 Available apps: {', '.join(self.list_apps())}")
            return 1

        available_files = self.list_app_files(app_name)
        if file_name not in available_files:
            print(self.colorize(f"❌ File '{file_name}' not found in app '{app_name}'!", Colors.RED))
            print(f"\n💡 Available files: {', '.join(available_files)}")
            return 1

        # Analyze the file
        try:
            analysis = self.analyzer.analyze_file(app_name, file_name)

            if not analysis or 'error' in analysis:
                print(self.colorize(f"❌ Could not analyze {app_name}/{file_name}", Colors.RED))
                if 'error' in analysis:
                    print(f"Error: {analysis['error']}")
                return 1

            # Display results
            self._display_file_analysis(analysis, verbose)
            
            # Show summary
            summary = self.analyzer.get_file_summary(app_name, file_name)
            self._display_summary(summary)

            # Show dependencies if verbose
            if verbose:
                deps = self.analyzer.find_dependencies(app_name, file_name)
                self._display_dependencies(deps)

            return 0

        except Exception as e:
            print(self.colorize(f"❌ Error analyzing file: {str(e)}", Colors.RED))
            if verbose:
                import traceback
                traceback.print_exc()
            return 1

    def run_usage_command(self, app_name: str, file_name: str, target: str, 
                         verbose: bool = False, export: Optional[str] = None) -> int:
        """Run the usage command to find where something is used."""
        print(self.colorize(f"🔍 Finding usages of '{target}' from {app_name}/{file_name}...", Colors.CYAN))
        print()

        # Validate app and file
        if app_name not in self.list_apps():
            print(self.colorize(f"❌ App '{app_name}' not found!", Colors.RED))
            return 1

        available_files = self.list_app_files(app_name)
        if file_name not in available_files:
            print(self.colorize(f"❌ File '{file_name}' not found in app '{app_name}'!", Colors.RED))
            return 1

        # Find usages
        try:
            usages = self.analyzer.find_usages(app_name, file_name, target)

            if not usages:
                print(self.colorize(f"❌ No usages found for '{target}'", Colors.YELLOW))
                print(f"\n💡 Make sure:")
                print(f"   • The element '{target}' exists in {app_name}/{file_name}")
                print(f"   • The element name is spelled correctly")
                print(f"   • Try using --list to see available elements")
                return 1

            # Display results
            self._display_usage_results(usages, verbose)

            # Export if requested
            if export:
                self._export_results(usages, export, app_name, file_name, target)
                print(self.colorize(f"\n✅ Results exported to {export}", Colors.GREEN))

            return 0

        except Exception as e:
            print(self.colorize(f"❌ Error finding usages: {str(e)}", Colors.RED))
            if verbose:
                import traceback
                traceback.print_exc()
            return 1

    def run_stats_command(self, app_name: Optional[str] = None) -> int:
        """Display statistics about the project or specific app."""
        if app_name:
            return self._show_app_stats(app_name)
        return self._show_project_stats()

    def _show_app_stats(self, app_name: str) -> int:
        """Show statistics for a specific app."""
        if app_name not in self.list_apps():
            print(self.colorize(f"❌ App '{app_name}' not found!", Colors.RED))
            return 1

        print(self.colorize(f"\n📊 Statistics for '{app_name}' app:", Colors.HEADER))
        print("=" * 60)

        files = self.list_app_files(app_name)
        stats = {
            'total_files': len(files),
            'total_classes': 0,
            'total_methods': 0,
            'total_functions': 0,
            'total_lines': 0,
            'file_details': []
        }

        for file_name in files:
            summary = self.analyzer.get_file_summary(app_name, file_name)
            if 'error' not in summary:
                stats['total_classes'] += summary.get('classes_count', 0)
                stats['total_methods'] += summary.get('methods_count', 0)
                stats['total_functions'] += summary.get('functions_count', 0)
                stats['total_lines'] += summary.get('total_lines', 0)
                stats['file_details'].append({
                    'file': file_name,
                    'summary': summary
                })

        print(f"\n📁 Files: {stats['total_files']}")
        print(f"🏗️  Classes: {stats['total_classes']}")
        print(f"⚡ Methods: {stats['total_methods']}")
        print(f"🔧 Functions: {stats['total_functions']}")
        print(f"📝 Total Lines: {stats['total_lines']}")

        print(f"\n{self.colorize('File Breakdown:', Colors.BOLD)}")
        for detail in sorted(stats['file_details'], 
                            key=lambda x: x['summary'].get('complexity_score', 0), 
                            reverse=True):
            file = detail['file']
            summary = detail['summary']
            print(f"  • {file}")
            print(f"    Classes: {summary.get('classes_count', 0)}, "
                  f"Methods: {summary.get('methods_count', 0)}, "
                  f"Functions: {summary.get('functions_count', 0)}, "
                  f"Complexity: {summary.get('complexity_score', 0)}")

        return 0

    def _show_project_stats(self) -> int:
        """Show overall project statistics."""
        print(self.colorize("\n📊 Project Statistics:", Colors.HEADER))
        print("=" * 60)

        apps = self.list_apps()
        total_files = 0
        total_classes = 0
        total_methods = 0
        app_stats = []

        for app_name in apps:
            files = self.list_app_files(app_name)
            app_classes = 0
            app_methods = 0

            for file_name in files:
                summary = self.analyzer.get_file_summary(app_name, file_name)
                if 'error' not in summary:
                    app_classes += summary.get('classes_count', 0)
                    app_methods += summary.get('methods_count', 0)

            total_files += len(files)
            total_classes += app_classes
            total_methods += app_methods

            app_stats.append({
                'name': app_name,
                'files': len(files),
                'classes': app_classes,
                'methods': app_methods
            })

        print(f"\n🎯 Apps: {len(apps)}")
        print(f"📁 Total Files: {total_files}")
        print(f"🏗️  Total Classes: {total_classes}")
        print(f"⚡ Total Methods: {total_methods}")

        print(f"\n{self.colorize('App Breakdown:', Colors.BOLD)}")
        for stat in sorted(app_stats, key=lambda x: x['classes'], reverse=True):
            print(f"  • {stat['name']}: {stat['files']} files, "
                  f"{stat['classes']} classes, {stat['methods']} methods")

        return 0

    def _display_file_analysis(self, analysis: dict, verbose: bool = False) -> None:
        """Display comprehensive file analysis results."""
        print(self.colorize("\n📊 File Analysis Results", Colors.HEADER))
        print("=" * 60)
        print(f"{self.colorize('📁 File:', Colors.BOLD)} {analysis['app']}/{analysis['file']}")
        print(f"{self.colorize('🏗️  Classes:', Colors.BOLD)} {len(analysis.get('classes', []))}")
        print(f"{self.colorize('⚡ Methods:', Colors.BOLD)} {sum(len(c.get('methods', [])) for c in analysis.get('classes', []))}")
        print(f"{self.colorize('🔧 Functions:', Colors.BOLD)} {len(analysis.get('functions', []))}")
        print(f"{self.colorize('📦 Imports:', Colors.BOLD)} {len(analysis.get('imports', []))}")
        print(f"{self.colorize('💾 Variables:', Colors.BOLD)} {len(analysis.get('variables', []))}")
        print(f"{self.colorize('🔤 Constants:', Colors.BOLD)} {len(analysis.get('constants', []))}")
        print()

        # Display classes with details
        if analysis.get('classes'):
            print(self.colorize("🏗️  Classes:", Colors.HEADER))
            for cls in analysis['classes']:
                print(f"\n  {self.colorize(cls['name'], Colors.BOLD)} (line {cls['line_number']})")
                
                if cls.get('base_classes'):
                    print(f"    Inherits: {', '.join(cls['base_classes'])}")
                
                if cls.get('decorators'):
                    print(f"    Decorators: {', '.join(cls['decorators'])}")
                
                if verbose and cls.get('docstring'):
                    print(f"    Doc: {cls['docstring'][:100]}...")

                if cls.get('methods'):
                    print(f"    Methods ({len(cls['methods'])}):")
                    for method in cls['methods']:
                        args_str = ', '.join(method['args'])
                        decorators = ''
                        if method.get('decorators'):
                            decorators = f" [{', '.join(method['decorators'])}]"
                        
                        method_type = ''
                        if method.get('is_static'):
                            method_type = ' [static]'
                        elif method.get('is_class_method'):
                            method_type = ' [classmethod]'
                        elif method.get('is_property'):
                            method_type = ' [property]'
                        
                        print(f"      • {method['name']}({args_str}){method_type}{decorators}")

                if cls.get('class_variables') and verbose:
                    print(f"    Variables: {', '.join(v['name'] for v in cls['class_variables'])}")

        # Display standalone functions
        if analysis.get('functions'):
            print(f"\n{self.colorize('🔧 Functions:', Colors.HEADER)}")
            for func in analysis['functions']:
                args_str = ', '.join(func['args'])
                decorators = ''
                if func.get('decorators'):
                    decorators = f" [{', '.join(func['decorators'])}]"
                returns = ''
                if func.get('returns'):
                    returns = f" -> {func['returns']}"
                print(f"  • {func['name']}({args_str}){returns}{decorators} (line {func['line_number']})")
                if verbose and func.get('docstring'):
                    print(f"    Doc: {func['docstring'][:100]}...")

        # Display constants
        if analysis.get('constants'):
            print(f"\n{self.colorize('🔤 Constants:', Colors.HEADER)}")
            for const in analysis['constants'][:10]:  # Limit to 10
                print(f"  • {const['name']} (line {const['line_number']})")
            if len(analysis['constants']) > 10:
                print(f"  ... and {len(analysis['constants']) - 10} more")

        # Display imports
        if analysis.get('imports') and verbose:
            print(f"\n{self.colorize('📦 Imports:', Colors.HEADER)}")
            for imp in analysis['imports'][:15]:  # Limit to 15
                alias_part = f" as {imp['alias']}" if imp.get('alias') and imp['alias'] != imp['module'].split('.')[-1] else ''
                print(f"  • {imp['module']}{alias_part}")
            if len(analysis['imports']) > 15:
                print(f"  ... and {len(analysis['imports']) - 15} more")

    def _display_usage_results(self, usages: List[dict], verbose: bool = False) -> None:
        """Display usage search results with grouping and statistics."""
        print(self.colorize("\n🔍 Usage Analysis Results", Colors.HEADER))
        print("=" * 60)
        print(f"{self.colorize(f'📋 Found {len(usages)} usage(s)', Colors.BOLD)}")
        print()

        # Group usages by type
        by_type = defaultdict(list)
        by_file = defaultdict(list)
        
        for usage in usages:
            by_type[usage.get('type', 'unknown')].append(usage)
            by_file[usage.get('file', 'unknown')].append(usage)

        # Display type summary
        print(self.colorize("📊 Usage Types:", Colors.BOLD))
        for usage_type, items in sorted(by_type.items(), key=lambda x: len(x[1]), reverse=True):
            print(f"  • {usage_type}: {len(items)}")
        print()

        # Display by file
        print(self.colorize("📁 Usages by File:", Colors.BOLD))
        for file_path, file_usages in sorted(by_file.items()):
            print(f"\n  {self.colorize(file_path, Colors.CYAN)} ({len(file_usages)} usage(s))")
            
            for usage in sorted(file_usages, key=lambda x: x.get('line', 0)):
                usage_type = usage.get('type', 'unknown')
                line_num = usage.get('line', '?')
                element = usage.get('element', '')
                
                # Color code by type
                type_color = Colors.GREEN
                if usage_type == 'import':
                    type_color = Colors.BLUE
                elif usage_type in ['instantiation', 'inheritance']:
                    type_color = Colors.YELLOW
                
                print(f"    {self.colorize(f'Line {line_num}', Colors.BOLD)}: "
                      f"{self.colorize(usage_type, type_color)}")
                
                if usage.get('context') and (verbose or len(file_usages) <= 5):
                    context = usage['context'][:100]
                    print(f"      {context}")

        print()

    def _display_summary(self, summary: dict) -> None:
        """Display file summary statistics."""
        if 'error' in summary:
            return

        print(self.colorize("\n📈 Summary Statistics", Colors.HEADER))
        print("=" * 60)
        print(f"Total Lines: {summary.get('total_lines', 0)}")
        print(f"Complexity Score: {summary.get('complexity_score', 0)}")
        print()

    def _display_dependencies(self, deps: dict) -> None:
        """Display file dependencies."""
        print(self.colorize("\n🔗 Dependencies", Colors.HEADER))
        print("=" * 60)
        
        if deps.get('django'):
            print(f"{self.colorize('Django/DRF:', Colors.BOLD)} {len(deps['django'])}")
            for dep in deps['django'][:5]:
                print(f"  • {dep}")
            if len(deps['django']) > 5:
                print(f"  ... and {len(deps['django']) - 5} more")

        if deps.get('internal'):
            print(f"\n{self.colorize('Internal:', Colors.BOLD)} {len(deps['internal'])}")
            for dep in deps['internal'][:5]:
                print(f"  • {dep}")
            if len(deps['internal']) > 5:
                print(f"  ... and {len(deps['internal']) - 5} more")

        if deps.get('third_party'):
            print(f"\n{self.colorize('Third Party:', Colors.BOLD)} {len(deps['third_party'])}")
            for dep in deps['third_party'][:5]:
                print(f"  • {dep}")
            if len(deps['third_party']) > 5:
                print(f"  ... and {len(deps['third_party']) - 5} more")

        if deps.get('relative'):
            print(f"\n{self.colorize('Relative:', Colors.BOLD)} {len(deps['relative'])}")
            for dep in deps['relative']:
                print(f"  • {dep}")
        print()

    def _export_results(self, usages: List[dict], output_file: str, 
                       app_name: str, file_name: str, target: str) -> None:
        """Export results to a file."""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"Usage Analysis Report\n")
                f.write(f"={'=' * 60}\n")
                f.write(f"Target: {target}\n")
                f.write(f"Source: {app_name}/{file_name}\n")
                f.write(f"Total Usages: {len(usages)}\n\n")

                by_file = defaultdict(list)
                for usage in usages:
                    by_file[usage.get('file', 'unknown')].append(usage)

                for file_path, file_usages in sorted(by_file.items()):
                    f.write(f"\n{file_path} ({len(file_usages)} usage(s))\n")
                    f.write("-" * 60 + "\n")
                    
                    for usage in sorted(file_usages, key=lambda x: x.get('line', 0)):
                        f.write(f"  Line {usage.get('line', '?')}: {usage.get('type', 'unknown')}\n")
                        if usage.get('context'):
                            f.write(f"    {usage['context']}\n")
                    f.write("\n")

        except Exception as e:
            print(self.colorize(f"⚠️  Warning: Could not export to {output_file}: {e}", Colors.YELLOW))


def main():
    """Main entry point with enhanced argument parsing."""
    parser = argparse.ArgumentParser(
        description="Django Project Usage Analyzer - Find code usages and dependencies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all apps in the project
  python ./tools/umain.py --list-apps

  # List files in an app
  python ./tools/umain.py --app users --list-files

  # Analyze a file (show classes, methods, functions)
  python ./tools/umain.py --app users --file views.py --list

  # Analyze with verbose output
  python ./tools/umain.py --app users --file views.py --list --verbose

  # Find usages of a class
  python ./tools/umain.py --app users --file services.py --usage UserService

  # Find usages with verbose details
  python ./tools/umain.py --app users --file services.py --usage UserService --verbose

  # Export results to file
  python ./tools/umain.py --app users --file services.py --usage UserService --export results.txt

  # Show project statistics
  python ./tools/umain.py --stats

  # Show app statistics
  python ./tools/umain.py --app users --stats

  # Disable colored output
  python ./tools/umain.py --app users --file views.py --list --no-color
  
  # Specify custom apps directory
  python ./tools/umain.py --base-dir apps --list-apps
        """
    )

    # Core arguments
    parser.add_argument('--app', help='Django app name')
    parser.add_argument('--file', help='File name within the app')
    parser.add_argument('--base-dir', default='api',
                       help='Base directory containing Django apps (default: api)')

    # Commands
    parser.add_argument('--list-apps', action='store_true', 
                       help='List all available Django apps')
    parser.add_argument('--list-files', action='store_true', 
                       help='List files in the specified app')
    parser.add_argument('--list', action='store_true', 
                       help='List classes and methods in the specified file')
    parser.add_argument('--usage', '-u', 
                       help='Find usages of the specified class/method/function')
    parser.add_argument('--stats', action='store_true',
                       help='Show statistics (project-wide or for specific app)')

    # Options
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Show detailed output')
    parser.add_argument('--export', '-e', 
                       help='Export results to specified file')
    parser.add_argument('--no-color', action='store_true',
                       help='Disable colored output')
    parser.add_argument('--debug', action='store_true',
                       help='Show debug information about paths')

    args = parser.parse_args()

    cli = UsageAnalyzerCLI(colored=not args.no_color, base_dir=args.base_dir)

    # Show debug info if requested
    if args.debug:
        print(cli.colorize("🔍 Debug Information:", Colors.HEADER))
        print(f"Current working directory: {Path.cwd()}")
        print(f"Script location: {Path(__file__).resolve()}")
        print(f"Detected project root: {cli.project_root}")
        print(f"Apps directory: {cli.base_dir}")
        print(f"Apps directory exists: {cli.base_dir.exists()}")
        print()

    # Handle list-apps command
    if args.list_apps:
        apps = cli.list_apps()
        if apps:
            print(cli.colorize(f"📋 Available Django apps ({len(apps)}):", Colors.HEADER))
            print(cli.colorize(f"📍 Location: {cli.base_dir}", Colors.CYAN))
            print()
            for app in apps:
                file_count = len(cli.list_app_files(app))
                print(f"  • {app} ({file_count} files)")
        else:
            print(cli.colorize("❌ No Django apps found!", Colors.RED))
            print()
            print("💡 Troubleshooting:")
            print(f"   • Current directory: {Path.cwd()}")
            print(f"   • Looking in: {cli.base_dir}")
            print(f"   • Try: python ./tools/umain.py --base-dir <your-apps-folder> --list-apps")
            print(f"   • Or run from project root (where manage.py is located)")
            print(f"   • Use --debug flag for more information")
        return 0

    # Handle stats command
    if args.stats:
        return cli.run_stats_command(args.app)

    # Handle list-files command
    if args.list_files:
        if not args.app:
            print(cli.colorize("❌ Please specify an app with --app", Colors.RED))
            return 1

        files = cli.list_app_files(args.app)
        if files:
            print(cli.colorize(f"📁 Files in '{args.app}' app ({len(files)}):", Colors.HEADER))
            for file in files:
                print(f"  • {file}")
        else:
            print(cli.colorize(f"❌ No files found in '{args.app}' app!", Colors.RED))
        return 0

    # Handle list command
    if args.list:
        if not args.app or not args.file:
            print(cli.colorize("❌ Please specify both --app and --file", Colors.RED))
            return 1

        return cli.run_list_command(args.app, args.file, args.verbose)

    # Handle usage command
    if args.usage:
        if not args.app or not args.file:
            print(cli.colorize("❌ Please specify both --app and --file", Colors.RED))
            return 1

        return cli.run_usage_command(args.app, args.file, args.usage, 
                                     args.verbose, args.export)

    # No valid command provided
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())