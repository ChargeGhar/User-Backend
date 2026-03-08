#!/usr/bin/env python3
"""
Hardcoded Points Finder Script
==============================

This script finds hardcoded points values across the app and suggests 
replacing them with AppConfig model values for better maintainability.

Based on your AppConfig values:
- POINTS_KYC: 30
- POINTS_PROFILE: 20  
- POINTS_SIGNUP: 50
- POINTS_REFERRAL_INVITER: 100
- POINTS_REFERRAL_INVITEE: 50
- POINTS_TOPUP: 10
- POINTS_RENTAL_COMPLETE: 5
- POINTS_TIMELY_RETURN: 50
- etc.

Usage:
    python tools/find_hardcoded_points.py .
"""

import os
import sys
import re
import ast
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# ============================================================================
# APPCONFIG POINTS MAPPING
# ============================================================================

APPCONFIG_POINTS = {
    # From your API response
    'POINTS_KYC': 30,
    'POINTS_PROFILE': 20,
    'POINTS_SIGNUP': 50,
    'POINTS_REFERRAL_INVITER': 100,
    'POINTS_REFERRAL_INVITEE': 50,
    'REFERRAL_BONUS_POINTS': 100,
    'POINTS_TOPUP': 10,
    'POINTS_RENTAL_COMPLETE': 5,
    'POINTS_TIMELY_RETURN': 50,
    'POINTS_TOPUP_PER_NPR': 100,
}

# Common hardcoded values that might correspond to these configs
COMMON_HARDCODED_VALUES = {
    30: ['POINTS_KYC'],
    20: ['POINTS_PROFILE'],
    50: ['POINTS_SIGNUP', 'POINTS_TIMELY_RETURN'],
    100: ['POINTS_REFERRAL_INVITER', 'REFERRAL_BONUS_POINTS', 'POINTS_TOPUP_PER_NPR'],
    10: ['POINTS_TOPUP'],
    5: ['POINTS_RENTAL_COMPLETE'],
}

# Context keywords that suggest points-related operations
POINTS_CONTEXT_KEYWORDS = [
    'points', 'award', 'deduct', 'bonus', 'reward', 'referral', 
    'signup', 'kyc', 'profile', 'rental', 'topup', 'timely', 'return'
]

@dataclass
class HardcodedPointsUsage:
    """Represents a hardcoded points usage"""
    file_path: str
    line_number: int
    line_content: str
    hardcoded_value: int
    context_before: List[str]
    context_after: List[str]
    suggested_configs: List[str]
    confidence: str
    explanation: str

class HardcodedPointsFinder:
    """Find hardcoded points values and suggest AppConfig replacements"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.usages: List[HardcodedPointsUsage] = []
        self.stats = {
            'files_scanned': 0,
            'files_with_issues': 0,
            'total_usages': 0,
            'by_value': {},
            'by_confidence': {'high': 0, 'medium': 0, 'low': 0}
        }
    
    def scan_project(self):
        """Scan entire project for hardcoded points"""
        print(f"📂 Project root: {self.project_root}")
        print(f"🔍 Scanning for hardcoded points values...")
        print("=" * 80)
        
        # Find all Python files
        py_files = list(self.project_root.rglob("*.py"))
        print(f"📁 Found {len(py_files)} Python files")
        print()
        
        # Scan each file
        for py_file in py_files:
            if self._should_skip(py_file):
                continue
            
            self._scan_file(py_file)
        
        # Generate report
        self._generate_report()
        
        print(f"\n✅ Scan complete!")
        print(f"   Files scanned: {self.stats['files_scanned']}")
        print(f"   Files with issues: {self.stats['files_with_issues']}")
        print(f"   Total usages found: {self.stats['total_usages']}")
    
    def _should_skip(self, file_path: Path) -> bool:
        """Check if file should be skipped"""
        skip_patterns = [
            '__pycache__',
            'migrations',
            '.venv',
            'venv',
            'env',
            '.git',
            'node_modules',
            '.pytest_cache',
            'htmlcov',
            '.tox',
            'dist',
            'build',
            '*.egg-info',
            'services_backup',
            'tasks_old.py',
        ]
        
        path_str = str(file_path)
        
        # Skip if any pattern matches
        if any(pattern in path_str for pattern in skip_patterns):
            return True
        
        # Skip tools directory unless specifically requested
        if 'tools/' in path_str and '--include-tools' not in sys.argv:
            return True
        
        # Only scan api/ directory for production code
        if not ('api/' in path_str or file_path.name in ['manage.py', 'celery.py']):
            return True
            
        return False
    
    def _scan_file(self, file_path: Path):
        """Scan single file for hardcoded points"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            self.stats['files_scanned'] += 1
            file_issues = 0
            
            # Scan each line for hardcoded values
            for line_no, line in enumerate(lines, 1):
                line_stripped = line.strip()
                
                # Skip comments and empty lines
                if not line_stripped or line_stripped.startswith('#'):
                    continue
                
                # Find potential hardcoded points values
                issues = self._find_hardcoded_values(line, line_no, lines, str(file_path))
                file_issues += len(issues)
                self.usages.extend(issues)
            
            if file_issues > 0:
                self.stats['files_with_issues'] += 1
                print(f"⚠️  {file_path.relative_to(self.project_root)}: {file_issues} issues")
            
        except Exception as e:
            print(f"❌ Error scanning {file_path}: {e}")
    
    def _find_hardcoded_values(self, line: str, line_no: int, lines: List[str], file_path: str) -> List[HardcodedPointsUsage]:
        """Find hardcoded points values in a line"""
        issues = []
        
        # Look for numeric values that match our AppConfig values
        for value, possible_configs in COMMON_HARDCODED_VALUES.items():
            # Pattern to find the value in various contexts
            patterns = [
                rf'\b{value}\b',  # Standalone number
                rf'[=,\(]\s*{value}\s*[,\)]',  # In function calls or assignments
                rf'points\s*[=:]\s*{value}',  # points = 50
                rf'award.*{value}',  # award_points(user, 50, ...)
                rf'{value}.*points',  # 50, 'SIGNUP'
            ]
            
            for pattern in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # Check if this looks like a points-related context
                    if self._is_points_context(line, lines, line_no):
                        # Get context
                        context_before = lines[max(0, line_no - 3):line_no - 1]
                        context_after = lines[line_no:min(len(lines), line_no + 2)]
                        
                        # Determine confidence and best config suggestion
                        confidence, best_config, explanation = self._analyze_context(
                            line, context_before, context_after, value, possible_configs
                        )
                        
                        usage = HardcodedPointsUsage(
                            file_path=file_path,
                            line_number=line_no,
                            line_content=line,
                            hardcoded_value=value,
                            context_before=context_before,
                            context_after=context_after,
                            suggested_configs=possible_configs,
                            confidence=confidence,
                            explanation=explanation
                        )
                        
                        issues.append(usage)
                        self.stats['total_usages'] += 1
                        self.stats['by_confidence'][confidence] += 1
                        
                        # Track by value
                        if value not in self.stats['by_value']:
                            self.stats['by_value'][value] = 0
                        self.stats['by_value'][value] += 1
                        
                        break  # Don't double-count the same line
        
        return issues
    
    def _is_points_context(self, line: str, lines: List[str], line_no: int) -> bool:
        """Check if the line is in a points-related context"""
        # Check current line
        line_lower = line.lower()
        if any(keyword in line_lower for keyword in POINTS_CONTEXT_KEYWORDS):
            return True
        
        # Check surrounding lines for context
        start = max(0, line_no - 3)
        end = min(len(lines), line_no + 2)
        context_lines = ' '.join(lines[start:end]).lower()
        
        return any(keyword in context_lines for keyword in POINTS_CONTEXT_KEYWORDS)
    
    def _analyze_context(self, line: str, context_before: List[str], context_after: List[str], 
                        value: int, possible_configs: List[str]) -> tuple[str, str, str]:
        """Analyze context to determine best config suggestion"""
        line_lower = line.lower()
        context_text = ' '.join(context_before + [line] + context_after).lower()
        
        # High confidence matches
        if 'kyc' in context_text and value == 30:
            return 'high', 'POINTS_KYC', 'KYC completion points'
        elif 'profile' in context_text and value == 20:
            return 'high', 'POINTS_PROFILE', 'Profile completion points'
        elif 'signup' in context_text and value == 50:
            return 'high', 'POINTS_SIGNUP', 'User signup bonus points'
        elif 'referral' in context_text and 'inviter' in context_text and value == 100:
            return 'high', 'POINTS_REFERRAL_INVITER', 'Referral inviter bonus'
        elif 'referral' in context_text and 'invitee' in context_text and value == 50:
            return 'high', 'POINTS_REFERRAL_INVITEE', 'Referral invitee bonus'
        elif 'topup' in context_text and value == 10:
            return 'high', 'POINTS_TOPUP', 'Topup bonus points'
        elif 'rental' in context_text and 'complete' in context_text and value == 5:
            return 'high', 'POINTS_RENTAL_COMPLETE', 'Rental completion points'
        elif 'timely' in context_text and 'return' in context_text and value == 50:
            return 'high', 'POINTS_TIMELY_RETURN', 'Timely return bonus'
        
        # Medium confidence - value matches but context is less specific
        elif len(possible_configs) == 1:
            return 'medium', possible_configs[0], f'Value {value} matches {possible_configs[0]}'
        
        # Low confidence - multiple possible matches
        else:
            return 'low', possible_configs[0], f'Value {value} could be {" or ".join(possible_configs)}'
    
    def _generate_report(self):
        """Generate detailed report"""
        if not self.usages:
            print("\n🎉 SUCCESS! No hardcoded points values found!")
            print("✅ Your codebase is using AppConfig properly!")
            return
        
        # Generate markdown report
        report_path = self.project_root / "hardcoded_points_report.md"
        with open(report_path, 'w') as f:
            f.write("# Hardcoded Points Values Report\n\n")
            f.write(f"**Generated:** {self._get_timestamp()}\n")
            f.write(f"**Project:** {self.project_root}\n\n")
            
            f.write("## 📊 Summary\n\n")
            f.write(f"- **Files Scanned:** {self.stats['files_scanned']}\n")
            f.write(f"- **Files with Issues:** {self.stats['files_with_issues']}\n")
            f.write(f"- **Total Usages:** {self.stats['total_usages']}\n\n")
            
            f.write("### By Value\n")
            for value, count in sorted(self.stats['by_value'].items()):
                f.write(f"- {value} points: {count} usages\n")
            
            f.write("\n### By Confidence\n")
            for confidence, count in self.stats['by_confidence'].items():
                f.write(f"- {confidence.title()}: {count} usages\n")
            
            f.write("\n## 🔍 Detailed Findings\n\n")
            
            # Group by file
            by_file = {}
            for usage in self.usages:
                file_path = usage.file_path
                if file_path not in by_file:
                    by_file[file_path] = []
                by_file[file_path].append(usage)
            
            for file_path, file_usages in sorted(by_file.items()):
                rel_path = Path(file_path).relative_to(self.project_root)
                f.write(f"### `{rel_path}`\n\n")
                f.write(f"**Issues found:** {len(file_usages)}\n\n")
                
                for i, usage in enumerate(file_usages, 1):
                    f.write(f"#### Issue #{i} - Line {usage.line_number}\n\n")
                    
                    # Current code
                    f.write("**Current Code:**\n")
                    f.write("```python\n")
                    for line in usage.context_before:
                        f.write(f"{line}\n")
                    f.write(f">>> {usage.line_content.strip()} # ⚠️ HARDCODED VALUE: {usage.hardcoded_value}\n")
                    for line in usage.context_after:
                        f.write(f"{line}\n")
                    f.write("```\n\n")
                    
                    # Suggestion
                    best_config = usage.suggested_configs[0]
                    f.write(f"**Fix Suggestion** (Confidence: {usage.confidence}):\n")
                    f.write("```python\n")
                    f.write(f"from api.config.services import AppConfigService\n")
                    f.write(f"config_service = AppConfigService()\n")
                    f.write(f"points = int(config_service.get_config_cached('{best_config}', {usage.hardcoded_value}))\n")
                    f.write("```\n\n")
                    
                    f.write(f"**Explanation:** {usage.explanation}\n\n")
                    
                    if usage.confidence == 'high':
                        f.write("✅ **Auto-fixable:** High confidence suggestion\n\n")
                    else:
                        f.write("⚠️ **Requires Review:** Manual verification needed\n\n")
                    
                    f.write("---\n\n")
        
        print(f"📄 Report generated: {report_path}")
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().strftime("%B %d, %Y")


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python tools/find_hardcoded_points.py <project_root>")
        sys.exit(1)
    
    project_root = sys.argv[1]
    finder = HardcodedPointsFinder(project_root)
    finder.scan_project()


if __name__ == "__main__":
    main()