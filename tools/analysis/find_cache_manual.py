#!/usr/bin/env python3
"""
Manual Cache Finder Tool
========================

Finds manual caching patterns in Django apps and suggests replacements with decorators.

Usage:
    python find_cache_manual.py --app content
    python find_cache_manual.py --app users  
    python find_cache_manual.py --all
"""

import os
import re
import argparse
from pathlib import Path
from typing import List, Dict, Tuple
import json


class CachePatternFinder:
    """Find manual caching patterns in Django apps"""
    
    def __init__(self):
        self.cache_patterns = [
            # Django cache patterns
            r'cache\.get\([\'"]([^\'\"]+)[\'"]',
            r'cache\.set\([\'"]([^\'\"]+)[\'"].*?timeout=(\d+)',
            r'cache\.delete\([\'"]([^\'\"]+)[\'"]',
            r'cached_\w+\s*=\s*cache\.get',
            
            # Cache key generation patterns
            r'cache_key\s*=\s*[\'"]([^\'\"]+)[\'"]',
            r'cache_key\s*=\s*f[\'"]([^\'\"]+)[\'"]',
            
            # Cache check patterns
            r'if\s+cached_\w+:',
            r'if\s+cache\.get\(',
            r'if\s+\w+_cache:',
        ]
        
        self.decorator_suggestions = {
            'view_cache': '@cached_response(timeout={})',
            'service_cache': '# Move to view with @cached_response(timeout={})',
            'search_cache': '# Remove caching, add @rate_limit instead',
            'financial_cache': '# REMOVE - Financial data should not be cached!',
        }
    
    def find_app_directories(self) -> List[str]:
        """Find all Django app directories"""
        api_dir = Path('api')
        if not api_dir.exists():
            return []
        
        apps = []
        for item in api_dir.iterdir():
            if item.is_dir() and not item.name.startswith('__'):
                # Check if it's a Django app (has models.py or views.py)
                if (item / 'models.py').exists() or (item / 'views.py').exists():
                    apps.append(item.name)
        
        return sorted(apps)
    
    def analyze_file(self, file_path: Path) -> Dict:
        """Analyze a single file for caching patterns"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return {'error': str(e)}
        
        findings = {
            'file': str(file_path),
            'cache_operations': [],
            'cache_keys': [],
            'suggestions': [],
            'severity': 'low'
        }
        
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Find cache.get patterns
            if 'cache.get(' in line_stripped:
                key_match = re.search(r'cache\.get\([\'"]([^\'\"]+)[\'"]', line_stripped)
                if key_match:
                    findings['cache_operations'].append({
                        'line': line_num,
                        'operation': 'GET',
                        'key': key_match.group(1),
                        'code': line_stripped
                    })
            
            # Find cache.set patterns
            if 'cache.set(' in line_stripped:
                set_match = re.search(r'cache\.set\([\'"]([^\'\"]+)[\'"].*?timeout=(\d+)', line_stripped)
                if set_match:
                    timeout = int(set_match.group(2))
                    findings['cache_operations'].append({
                        'line': line_num,
                        'operation': 'SET',
                        'key': set_match.group(1),
                        'timeout': timeout,
                        'code': line_stripped
                    })
                    
                    # Determine cache type and suggestion
                    key = set_match.group(1).lower()
                    if any(word in key for word in ['wallet', 'balance', 'payment', 'transaction']):
                        findings['suggestions'].append({
                            'line': line_num,
                            'type': 'financial_cache',
                            'suggestion': self.decorator_suggestions['financial_cache'],
                            'severity': 'critical'
                        })
                        findings['severity'] = 'critical'
                    elif 'search' in key:
                        findings['suggestions'].append({
                            'line': line_num,
                            'type': 'search_cache',
                            'suggestion': self.decorator_suggestions['search_cache'],
                            'severity': 'medium'
                        })
                    elif file_path.name == 'views.py':
                        findings['suggestions'].append({
                            'line': line_num,
                            'type': 'view_cache',
                            'suggestion': self.decorator_suggestions['view_cache'].format(timeout),
                            'severity': 'low'
                        })
                    else:
                        findings['suggestions'].append({
                            'line': line_num,
                            'type': 'service_cache',
                            'suggestion': self.decorator_suggestions['service_cache'].format(timeout),
                            'severity': 'medium'
                        })
            
            # Find cache.delete patterns
            if 'cache.delete(' in line_stripped:
                del_match = re.search(r'cache\.delete\([\'"]([^\'\"]+)[\'"]', line_stripped)
                if del_match:
                    findings['cache_operations'].append({
                        'line': line_num,
                        'operation': 'DELETE',
                        'key': del_match.group(1),
                        'code': line_stripped
                    })
            
            # Find cache key definitions
            if 'cache_key' in line_stripped:
                key_match = re.search(r'cache_key\s*=\s*[\'"]([^\'\"]+)[\'"]', line_stripped)
                if key_match:
                    findings['cache_keys'].append({
                        'line': line_num,
                        'key': key_match.group(1),
                        'code': line_stripped
                    })
        
        return findings
    
    def analyze_app(self, app_name: str) -> Dict:
        """Analyze all files in a Django app"""
        app_path = Path('api') / app_name
        if not app_path.exists():
            return {'error': f'App {app_name} not found'}
        
        results = {
            'app': app_name,
            'files_analyzed': 0,
            'files_with_cache': 0,
            'total_cache_operations': 0,
            'critical_issues': 0,
            'files': {}
        }
        
        # Analyze Python files
        for py_file in app_path.glob('*.py'):
            if py_file.name.startswith('__'):
                continue
                
            results['files_analyzed'] += 1
            findings = self.analyze_file(py_file)
            
            if findings.get('cache_operations') or findings.get('cache_keys'):
                results['files_with_cache'] += 1
                results['total_cache_operations'] += len(findings.get('cache_operations', []))
                results['files'][py_file.name] = findings
                
                # Count critical issues
                for suggestion in findings.get('suggestions', []):
                    if suggestion.get('severity') == 'critical':
                        results['critical_issues'] += 1
        
        return results
    
    def generate_report(self, results: Dict) -> str:
        """Generate a formatted report"""
        if 'error' in results:
            return f"❌ Error: {results['error']}"
        
        app_name = results['app']
        report = [
            f"\n🔍 **Manual Cache Analysis: {app_name.upper()} App**",
            f"=" * 50,
            f"📊 **Summary:**",
            f"   • Files analyzed: {results['files_analyzed']}",
            f"   • Files with caching: {results['files_with_cache']}",
            f"   • Total cache operations: {results['total_cache_operations']}",
            f"   • Critical issues: {results['critical_issues']}",
            ""
        ]
        
        if results['critical_issues'] > 0:
            report.append("🚨 **CRITICAL ISSUES FOUND!**")
            report.append("")
        
        for filename, findings in results['files'].items():
            report.append(f"📁 **{filename}**")
            report.append("-" * 30)
            
            # Show cache operations
            if findings.get('cache_operations'):
                report.append("🔧 **Cache Operations:**")
                for op in findings['cache_operations']:
                    timeout_info = f" (timeout: {op['timeout']}s)" if 'timeout' in op else ""
                    report.append(f"   Line {op['line']}: {op['operation']} '{op['key']}'{timeout_info}")
                    report.append(f"   Code: {op['code']}")
                report.append("")
            
            # Show suggestions
            if findings.get('suggestions'):
                report.append("💡 **Suggestions:**")
                for suggestion in findings['suggestions']:
                    severity_icon = {"critical": "🚨", "medium": "⚠️", "low": "ℹ️"}
                    icon = severity_icon.get(suggestion['severity'], "ℹ️")
                    report.append(f"   {icon} Line {suggestion['line']}: {suggestion['suggestion']}")
                report.append("")
            
            report.append("")
        
        # Add recommendations
        if results['files_with_cache'] > 0:
            report.extend([
                "🎯 **Recommended Actions:**",
                "",
                "1. **Replace manual caching in views:**",
                "   ```python",
                "   @cached_response(timeout=3600)  # 1 hour",
                "   def get(self, request):",
                "       # Remove cache.get/set logic",
                "   ```",
                "",
                "2. **Remove caching from services:**",
                "   - Move caching logic to view decorators",
                "   - Keep services focused on business logic",
                "",
                "3. **Critical fixes:**",
                "   - Remove ALL caching from financial data",
                "   - Replace search caching with rate limiting",
                "",
                "4. **Use Common.md patterns:**",
                "   - Follow MVP caching strategy",
                "   - Use BaseAPIView with decorators",
                ""
            ])
        else:
            report.append("✅ **No manual caching found - Good job!**")
        
        return "\n".join(report)
    
    def save_results(self, results: Dict, output_file: str = None):
        """Save results to JSON file"""
        if not output_file:
            output_file = f"cache_analysis_{results['app']}.json"
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"📄 Results saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Find manual caching patterns in Django apps')
    parser.add_argument('--app', help='Specific app to analyze')
    parser.add_argument('--all', action='store_true', help='Analyze all apps')
    parser.add_argument('--save', action='store_true', help='Save results to JSON file')
    parser.add_argument('--output', help='Output file name')
    
    args = parser.parse_args()
    
    finder = CachePatternFinder()
    
    if args.all:
        apps = finder.find_app_directories()
        print(f"🔍 Found {len(apps)} Django apps: {', '.join(apps)}")
        
        total_issues = 0
        for app in apps:
            results = finder.analyze_app(app)
            report = finder.generate_report(results)
            print(report)
            
            if args.save:
                finder.save_results(results)
            
            total_issues += results.get('critical_issues', 0)
        
        print(f"\n🎯 **Overall Summary:**")
        print(f"   • Apps analyzed: {len(apps)}")
        print(f"   • Total critical issues: {total_issues}")
        
    elif args.app:
        results = finder.analyze_app(args.app)
        report = finder.generate_report(results)
        print(report)
        
        if args.save:
            finder.save_results(results, args.output)
    
    else:
        print("❌ Please specify --app <name> or --all")
        print("\nAvailable apps:")
        apps = finder.find_app_directories()
        for app in apps:
            print(f"   • {app}")


if __name__ == '__main__':
    main()