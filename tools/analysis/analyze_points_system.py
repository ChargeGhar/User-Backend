#!/usr/bin/env python3
"""
PowerBank Points System Analyzer
Analyzes all points awarding logic across the application and compares with requirements.

Usage:
    python tools/analyze_points_system.py                    # Full analysis
    python tools/analyze_points_system.py --missing          # Show missing implementations
    python tools/analyze_points_system.py --extra            # Show extra implementations
    python tools/analyze_points_system.py --generate-config  # Generate AppConfig fixture
    python tools/analyze_points_system.py --summary          # Quick summary
"""

import os
import re
import ast
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Set, Any
from dataclasses import dataclass
import json

@dataclass
class PointsRequirement:
    """Points requirement from scenarios.txt"""
    action: str
    points: str
    trigger: str
    recipient: str
    source_key: str  # For mapping to code

@dataclass
class PointsImplementation:
    """Points implementation found in code"""
    file_path: str
    line_number: int
    function_name: str
    points_value: str
    source: str
    description: str
    code_snippet: str
    context: str

class PowerBankPointsAnalyzer:
    """Comprehensive points system analyzer"""
    
    def __init__(self):
        self.requirements: List[PointsRequirement] = []
        self.implementations: List[PointsImplementation] = []
        self.source_patterns = {
            'SIGNUP': ['signup', 'register', 'registration'],
            'REFERRAL_INVITER': ['referral.*inviter', 'inviter.*referral'],
            'REFERRAL_INVITEE': ['referral.*invitee', 'invitee.*referral'],
            'TOPUP': ['topup', 'top.up', 'wallet.*add'],
            'RENTAL_COMPLETE': ['rental.*complete', 'complete.*rental'],
            'TIMELY_RETURN': ['timely.*return', 'return.*timely'],
            'COUPON': ['coupon', 'promo'],
            'KYC': ['kyc', 'verification'],
            'PROFILE': ['profile.*complete', 'complete.*profile'],
            'ACHIEVEMENT': ['achievement', 'unlock']
        }
        
    def load_requirements(self, scenarios_file: str = "session/secenarios.txt") -> None:
        """Load requirements from scenarios.txt"""
        try:
            with open(scenarios_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the markdown table
            lines = content.strip().split('\n')
            for line in lines[2:]:  # Skip header and separator
                if '|' in line and line.strip():
                    parts = [p.strip() for p in line.split('|')[1:-1]]  # Remove empty first/last
                    if len(parts) >= 4:
                        action = parts[0]
                        points = parts[1]
                        trigger = parts[2]
                        recipient = parts[3]
                        
                        # Map to source key
                        source_key = self._map_action_to_source(action)
                        
                        self.requirements.append(PointsRequirement(
                            action=action,
                            points=points,
                            trigger=trigger,
                            recipient=recipient,
                            source_key=source_key
                        ))
                        
        except FileNotFoundError:
            print(f"❌ Requirements file not found: {scenarios_file}")
        except Exception as e:
            print(f"❌ Error loading requirements: {e}")
    
    def _map_action_to_source(self, action: str) -> str:
        """Map action description to source key"""
        action_lower = action.lower()
        
        if 'signup' in action_lower or 'registration' in action_lower:
            return 'SIGNUP'
        elif 'referral' in action_lower and 'inviter' in action_lower:
            return 'REFERRAL_INVITER'
        elif 'referral' in action_lower and 'invitee' in action_lower:
            return 'REFERRAL_INVITEE'
        elif 'top-up' in action_lower or 'topup' in action_lower:
            return 'TOPUP'
        elif 'rental' in action_lower and 'completed' in action_lower:
            return 'RENTAL_COMPLETE'
        elif 'timely' in action_lower and 'return' in action_lower:
            return 'TIMELY_RETURN'
        elif 'coupon' in action_lower:
            return 'COUPON'
        elif 'kyc' in action_lower:
            return 'KYC'
        elif 'profile' in action_lower:
            return 'PROFILE'
        elif 'achievement' in action_lower:
            return 'ACHIEVEMENT'
        else:
            return 'UNKNOWN'
    
    def scan_codebase(self) -> None:
        """Scan entire codebase for points awarding logic"""
        api_dir = Path("api")
        
        # Patterns to find points awarding
        patterns = [
            r'award_points',
            r'\.delay\(',
            r'points',
            r'SIGNUP|REFERRAL|TOPUP|RENTAL|COUPON|KYC|PROFILE|ACHIEVEMENT',
            r'SOURCE_CHOICES',
            r'100.*points',
            r'50.*points',
            r'10.*points',
            r'5.*points'
        ]
        
        for py_file in api_dir.rglob("*.py"):
            self._scan_file(py_file, patterns)
    
    def _scan_file(self, file_path: Path, patterns: List[str]) -> None:
        """Scan individual file for points logic"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                # Look for points awarding patterns
                keywords = ['award_points', 'points', 'SIGNUP', 'REFERRAL', 'TOPUP', 'RENTAL', 'COUPON', 'KYC', 'ACHIEVEMENT', '.delay(', '100', '50', '10', '5']
                if any(keyword in line for keyword in keywords):
                    self._analyze_line(file_path, line_num, line, lines, content)
                    
        except Exception as e:
            print(f"⚠️  Error scanning {file_path}: {e}")
    
    def _analyze_line(self, file_path: Path, line_num: int, line: str, all_lines: List[str], content: str) -> None:
        """Analyze a specific line for points logic"""
        line_clean = line.strip()
        
        # Skip comments and empty lines
        if not line_clean or line_clean.startswith('#'):
            return
        
        # Pattern 1: Direct points awarding calls
        award_patterns = [
            r'award_points_task\.delay\([^,]+,\s*(\d+),\s*[\'"]([A-Z_]+)[\'"],\s*[\'"]([^\'\"]+)[\'"]',
            r'award_points\([^,]+,\s*(\d+),\s*[\'"]([A-Z_]+)[\'"],\s*[\'"]([^\'\"]+)[\'"]',
            r'\.delay\([^,]*,\s*(\d+),\s*[\'"]([A-Z_]+)[\'"]',
            r'award_topup_points_task\.delay\(',
            r'award_rental_completion_points\.delay\(',
            r'(\d+),\s*[\'"]([A-Z_]+)[\'"],\s*[\'"]([^\'\"]+)[\'"]'
        ]
        
        for pattern in award_patterns:
            match = re.search(pattern, line)
            if match:
                groups = match.groups()
                
                # Handle different pattern matches
                if len(groups) >= 3:
                    points = groups[-3] if len(groups) >= 3 else groups[0]
                    source = groups[-2] if len(groups) >= 2 else 'UNKNOWN'
                    description = groups[-1] if len(groups) >= 3 else 'No description'
                elif len(groups) >= 2:
                    points = groups[0]
                    source = groups[1]
                    description = 'From pattern match'
                else:
                    # Special handling for specific task calls
                    if 'award_topup_points_task' in line:
                        points = '10'  # Known from code
                        source = 'TOPUP'
                        description = 'Top-up points task'
                    elif 'award_rental_completion_points' in line:
                        points = '5'  # Base points
                        source = 'RENTAL_COMPLETE'
                        description = 'Rental completion points'
                    else:
                        continue
                
                # Get function context
                function_name = self._get_function_context(all_lines, line_num)
                context = self._get_code_context(all_lines, line_num)
                
                self.implementations.append(PointsImplementation(
                    file_path=str(file_path),
                    line_number=line_num,
                    function_name=function_name,
                    points_value=points,
                    source=source,
                    description=description,
                    code_snippet=line_clean,
                    context=context
                ))
        
        # Pattern 2: Hardcoded points values and specific implementations
        hardcoded_patterns = [
            r'(\d+)\s*#.*points',
            r'points\s*=\s*(\d+)',
            r'[\'"]points[\'"]:\s*(\d+)',
            r'base_points\s*=\s*(\d+)',
            r'bonus_points\s*=\s*(\d+)',
            r'inviter_points_awarded\s*=\s*(\d+)',
            r'invitee_points_awarded\s*=\s*(\d+)'
        ]
        
        # Special cases for known implementations
        special_cases = [
            ('10 points per NPR 100', 'TOPUP', 'award_topup_points_task'),
            ('100.*points.*inviter', 'REFERRAL_INVITER', 'complete_referral'),
            ('50.*points.*invitee', 'REFERRAL_INVITEE', 'complete_referral'),
            ('base_points.*5', 'RENTAL_COMPLETE', 'award_rental_completion_points'),
            ('bonus_points.*5', 'TIMELY_RETURN', 'award_rental_completion_points')
        ]
        
        for pattern_text, source, func_hint in special_cases:
            if re.search(pattern_text, line, re.IGNORECASE):
                points_match = re.search(r'(\d+)', pattern_text)
                if points_match:
                    points = points_match.group(1)
                    function_name = self._get_function_context(all_lines, line_num)
                    context = self._get_code_context(all_lines, line_num)
                    
                    self.implementations.append(PointsImplementation(
                        file_path=str(file_path),
                        line_number=line_num,
                        function_name=function_name,
                        points_value=points,
                        source=source,
                        description=f"Special case: {pattern_text}",
                        code_snippet=line_clean,
                        context=context
                    ))
        
        for pattern in hardcoded_patterns:
            match = re.search(pattern, line)
            if match:
                points = match.group(1)
                source = self._extract_source_from_context(all_lines, line_num)
                
                # Skip if we don't have a clear source
                if source == 'UNKNOWN':
                    continue
                    
                function_name = self._get_function_context(all_lines, line_num)
                context = self._get_code_context(all_lines, line_num)
                
                self.implementations.append(PointsImplementation(
                    file_path=str(file_path),
                    line_number=line_num,
                    function_name=function_name,
                    points_value=points,
                    source=source,
                    description="Hardcoded points value",
                    code_snippet=line_clean,
                    context=context
                ))
    
    def _get_function_context(self, lines: List[str], line_num: int) -> str:
        """Get the function name containing this line"""
        for i in range(line_num - 1, -1, -1):
            line = lines[i].strip()
            if line.startswith('def ') or line.startswith('class '):
                match = re.match(r'(def|class)\s+([a-zA-Z_][a-zA-Z0-9_]*)', line)
                if match:
                    return match.group(2)
        return "unknown"
    
    def _get_code_context(self, lines: List[str], line_num: int, context_lines: int = 3) -> str:
        """Get surrounding code context"""
        start = max(0, line_num - context_lines - 1)
        end = min(len(lines), line_num + context_lines)
        
        context = []
        for i in range(start, end):
            prefix = ">>> " if i == line_num - 1 else "    "
            context.append(f"{prefix}{lines[i]}")
        
        return '\n'.join(context)
    
    def _extract_source_from_context(self, lines: List[str], line_num: int) -> str:
        """Extract source type from surrounding context"""
        # Look in surrounding lines for source indicators
        start = max(0, line_num - 10)
        end = min(len(lines), line_num + 5)
        
        context = ' '.join(lines[start:end]).upper()
        
        for source, keywords in self.source_patterns.items():
            if any(re.search(keyword.upper(), context) for keyword in keywords):
                return source
        
        return "UNKNOWN"
    
    def analyze_compliance(self) -> Dict[str, Any]:
        """Analyze compliance between requirements and implementations"""
        implemented_sources = {impl.source for impl in self.implementations}
        required_sources = {req.source_key for req in self.requirements}
        
        missing = required_sources - implemented_sources
        extra = implemented_sources - required_sources
        
        # Detailed analysis
        compliance_details = {}
        
        for req in self.requirements:
            matching_impls = [impl for impl in self.implementations if impl.source == req.source_key]
            
            compliance_details[req.source_key] = {
                'requirement': req,
                'implementations': matching_impls,
                'status': 'implemented' if matching_impls else 'missing',
                'points_match': self._check_points_match(req, matching_impls)
            }
        
        return {
            'total_requirements': len(self.requirements),
            'total_implementations': len(self.implementations),
            'implemented_count': len(implemented_sources & required_sources),
            'missing_count': len(missing),
            'extra_count': len(extra),
            'missing_sources': list(missing),
            'extra_sources': list(extra),
            'compliance_details': compliance_details,
            'compliance_percentage': (len(implemented_sources & required_sources) / len(required_sources)) * 100 if required_sources else 100
        }
    
    def _check_points_match(self, requirement: PointsRequirement, implementations: List[PointsImplementation]) -> bool:
        """Check if implemented points match requirement"""
        if not implementations:
            return False
        
        req_points = self._extract_points_from_requirement(requirement.points)
        
        for impl in implementations:
            try:
                impl_points = int(impl.points_value)
                if impl_points == req_points:
                    return True
            except ValueError:
                continue
        
        return False
    
    def _extract_points_from_requirement(self, points_str: str) -> int:
        """Extract numeric points from requirement string"""
        # Handle cases like "+50", "Variable", "+10 per NPR 100"
        if 'variable' in points_str.lower():
            return -1  # Special case for variable points
        
        match = re.search(r'(\d+)', points_str)
        return int(match.group(1)) if match else 0
    
    def generate_report(self) -> str:
        """Generate comprehensive analysis report"""
        analysis = self.analyze_compliance()
        
        report = []
        report.append("🔍 POWERBANK POINTS SYSTEM ANALYSIS REPORT")
        report.append("=" * 80)
        
        # Summary
        report.append(f"\n📊 SUMMARY:")
        report.append(f"   Total Requirements: {analysis['total_requirements']}")
        report.append(f"   Total Implementations: {analysis['total_implementations']}")
        report.append(f"   Compliance: {analysis['compliance_percentage']:.1f}%")
        report.append(f"   ✅ Implemented: {analysis['implemented_count']}")
        report.append(f"   ❌ Missing: {analysis['missing_count']}")
        report.append(f"   ⚠️  Extra: {analysis['extra_count']}")
        
        # Detailed compliance
        report.append(f"\n📋 DETAILED COMPLIANCE ANALYSIS:")
        report.append("-" * 60)
        
        for source, details in analysis['compliance_details'].items():
            req = details['requirement']
            impls = details['implementations']
            status = details['status']
            points_match = details['points_match']
            
            status_icon = "✅" if status == 'implemented' else "❌"
            points_icon = "✅" if points_match else "⚠️"
            
            report.append(f"\n{status_icon} {req.action}")
            report.append(f"   Required: {req.points} points")
            report.append(f"   Source: {source}")
            report.append(f"   Status: {status}")
            
            if impls:
                report.append(f"   {points_icon} Implementations ({len(impls)}):")
                for impl in impls:
                    report.append(f"      • {impl.points_value} points in {impl.function_name}()")
                    report.append(f"        File: {impl.file_path}:{impl.line_number}")
                    report.append(f"        Code: {impl.code_snippet}")
            else:
                report.append(f"   ❌ No implementation found")
        
        # Missing implementations
        if analysis['missing_sources']:
            report.append(f"\n❌ MISSING IMPLEMENTATIONS:")
            report.append("-" * 40)
            for source in analysis['missing_sources']:
                req = next((r for r in self.requirements if r.source_key == source), None)
                if req:
                    report.append(f"   • {req.action} ({req.points} points)")
                    report.append(f"     Trigger: {req.trigger}")
        
        # Extra implementations
        if analysis['extra_sources']:
            report.append(f"\n⚠️  EXTRA IMPLEMENTATIONS (Not in requirements):")
            report.append("-" * 50)
            for source in analysis['extra_sources']:
                impls = [impl for impl in self.implementations if impl.source == source]
                for impl in impls:
                    report.append(f"   • {source}: {impl.points_value} points")
                    report.append(f"     File: {impl.file_path}:{impl.line_number}")
                    report.append(f"     Function: {impl.function_name}()")
        
        # All implementations
        report.append(f"\n🔧 ALL IMPLEMENTATIONS FOUND:")
        report.append("-" * 40)
        
        grouped_impls = {}
        for impl in self.implementations:
            if impl.source not in grouped_impls:
                grouped_impls[impl.source] = []
            grouped_impls[impl.source].append(impl)
        
        for source, impls in sorted(grouped_impls.items()):
            report.append(f"\n📍 {source}:")
            for impl in impls:
                report.append(f"   • {impl.points_value} points - {impl.function_name}()")
                report.append(f"     📁 {impl.file_path}:{impl.line_number}")
                report.append(f"     💬 {impl.description}")
                report.append(f"     📝 {impl.code_snippet}")
        
        return '\n'.join(report)
    
    def generate_appconfig_fixture(self) -> str:
        """Generate AppConfig fixture for centralized points configuration"""
        fixture_data = []
        
        for req in self.requirements:
            if req.source_key != 'UNKNOWN':
                points_value = self._extract_points_from_requirement(req.points)
                if points_value > 0:  # Skip variable points
                    fixture_data.append({
                        "model": "config.appconfig",
                        "pk": len(fixture_data) + 1,
                        "fields": {
                            "key": f"POINTS_{req.source_key}",
                            "value": str(points_value),
                            "description": f"Points awarded for {req.action}",
                            "is_active": True
                        }
                    })
        
        # Add special configurations
        special_configs = [
            {
                "key": "POINTS_TOPUP_PER_NPR",
                "value": "100",
                "description": "NPR amount per points award for top-up (10 points per 100 NPR)"
            },
            {
                "key": "POINTS_TOPUP_RATIO",
                "value": "10",
                "description": "Points awarded per POINTS_TOPUP_PER_NPR amount"
            }
        ]
        
        for config in special_configs:
            fixture_data.append({
                "model": "config.appconfig",
                "pk": len(fixture_data) + 1,
                "fields": {
                    **config,
                    "is_active": True
                }
            })
        
        return json.dumps(fixture_data, indent=2)
    
    def print_summary(self) -> None:
        """Print quick summary"""
        analysis = self.analyze_compliance()
        
        print("🎯 POINTS SYSTEM QUICK SUMMARY")
        print("=" * 50)
        print(f"Compliance: {analysis['compliance_percentage']:.1f}%")
        print(f"✅ Implemented: {analysis['implemented_count']}/{analysis['total_requirements']}")
        print(f"❌ Missing: {analysis['missing_count']}")
        print(f"⚠️  Extra: {analysis['extra_count']}")
        
        if analysis['missing_sources']:
            print(f"\n❌ Missing: {', '.join(analysis['missing_sources'])}")
        
        if analysis['extra_sources']:
            print(f"⚠️  Extra: {', '.join(analysis['extra_sources'])}")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='PowerBank Points System Analyzer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/analyze_points_system.py                    # Full analysis
  python tools/analyze_points_system.py --missing          # Show missing only
  python tools/analyze_points_system.py --extra            # Show extra only  
  python tools/analyze_points_system.py --generate-config  # Generate fixture
  python tools/analyze_points_system.py --summary          # Quick summary
        """
    )
    
    parser.add_argument('--missing', action='store_true', help='Show only missing implementations')
    parser.add_argument('--extra', action='store_true', help='Show only extra implementations')
    parser.add_argument('--generate-config', action='store_true', help='Generate AppConfig fixture')
    parser.add_argument('--summary', action='store_true', help='Show quick summary only')
    parser.add_argument('--output', type=str, help='Output file for report')
    
    args = parser.parse_args()
    
    # Initialize analyzer
    analyzer = PowerBankPointsAnalyzer()
    
    # Load requirements and scan codebase
    print("🔍 Loading requirements from session/secenarios.txt...")
    analyzer.load_requirements()
    
    print("🔍 Scanning codebase for points implementations...")
    analyzer.scan_codebase()
    
    # Handle different modes
    if args.summary:
        analyzer.print_summary()
        return
    
    if args.generate_config:
        print("🔧 Generating AppConfig fixture...")
        fixture = analyzer.generate_appconfig_fixture()
        
        output_file = args.output or "fixtures/points_config.json"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w') as f:
            f.write(fixture)
        
        print(f"✅ AppConfig fixture generated: {output_file}")
        return
    
    # Generate full report
    report = analyzer.generate_report()
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(report)
        print(f"✅ Report saved to: {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()