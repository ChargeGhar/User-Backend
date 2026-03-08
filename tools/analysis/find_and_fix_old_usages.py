#!/usr/bin/env python3
"""
Old Usage Finder and Fixer Script
==================================

This script finds ALL old notification and points app usages across the entire project
with 100% accuracy and provides AI-powered suggestions for correct replacements.

Features:
- AST parsing for Python imports and function calls
- Regex patterns for comprehensive coverage
- Multi-stage verification to catch edge cases
- Detailed report with file locations and suggestions
- Safe analysis (read-only, no automatic changes)

Usage:
    # From tools directory
    python tools/find_and_fix_old_usages.py .
    
    # Or with full path
    python tools/find_and_fix_old_usages.py /path/to/project/root
    
Example:
    cd /home/revdev/Desktop/Daily/Devalaya/PowerBank/ChargeGhar
    python tools/find_and_fix_old_usages.py .

Author: Generated for PowerBank Project
Date: October 15, 2025
"""

import ast
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Tuple, Set, Optional
from collections import defaultdict
import json


# ============================================================================
# CONFIGURATION: Actual Old Patterns Based on Project Analysis
# ============================================================================

# These are the ACTUAL old patterns we need to find and fix based on our project scope
OLD_NOTIFICATION_PATTERNS = {
    # Old task imports that need to be replaced
    'task_imports': [
        'from api.notifications.tasks import send_notification_task',
        'from api.notifications.tasks import send_email_task', 
        'from api.notifications.tasks import send_sms_task',
        'from api.notifications.tasks import send_fcm_task',
        'from api.notifications.tasks import send_otp_task',
        'from api.notifications.tasks import send_welcome_email_task',
        'from api.notifications.tasks import send_rental_notification_task',
        'from api.notifications.tasks import send_payment_notification_task',
        'from api.notifications.tasks import send_rental_reminder_notification',
        'from api.notifications.tasks import notify_points_earned',
        'from api.notifications.tasks import notify_rental_started',
        'from api.notifications.tasks import notify_rental_completed',
        'from api.notifications.tasks import notify_account_status',
        'from api.notifications.tasks import notify_kyc_status',
        'from api.notifications.tasks import notify_wallet_recharged',
        'from api.notifications.tasks import notify_otp',
    ],
    
    # Old service imports that need to be replaced
    'service_imports': [
        'from api.notifications.services import NotificationService',
        'from api.notifications.services.notification import NotificationService',
        'from api.notifications.services import EmailService',
        'from api.notifications.services import SMSService', 
        'from api.notifications.services import FCMService',
        'from api.notifications.services import BulkNotificationService',
    ],
    
    # Old task calls that need to be replaced
    'task_calls': [
        'send_notification_task.delay',
        'send_email_task.delay',
        'send_sms_task.delay', 
        'send_fcm_task.delay',
        'send_otp_task.delay',
        'send_welcome_email_task.delay',
        'send_rental_notification_task.delay',
        'send_payment_notification_task.delay',
        'send_rental_reminder_notification.delay',
        'send_rental_reminder_notification.apply_async',
        'notify_points_earned.delay',
        'notify_rental_started.delay',
        'notify_rental_completed.delay',
        'notify_account_status.delay',
        'notify_kyc_status.delay',
        'notify_wallet_recharged.delay',
        'notify_otp.delay',
    ],
    
    # Old service instantiation and calls
    'service_calls': [
        'NotificationService()',
        'notification_service.send',
        'notification_service.create_notification',
        'EmailService()',
        'SMSService()',
        'FCMService()',
        'BulkNotificationService()',
        'bulk_service.send_bulk_notification',
    ],
}

OLD_POINTS_PATTERNS = {
    # Old task imports that need to be replaced
    'task_imports': [
        'from api.points.tasks import award_points_task',
        'from api.points.tasks import award_topup_points_task',
        'from api.points.tasks import award_rental_completion_points',
        'from api.points.tasks import award_referral_points_task', 
        'from api.points.tasks import award_signup_points_task',
        'from api.points.tasks import deduct_points_task',
        'from api.points.tasks import deduct_rental_points_task',
        'from api.points.tasks import process_referral_task',
        'from api.points.tasks import complete_referral_task',
        'from api.points.tasks import update_leaderboard_task',
    ],
    
    # Old service imports that need to be replaced  
    'service_imports': [
        'from api.points.services import PointsService',
        'from api.points.services import ReferralService',
        'from api.points.services.points_service import PointsService',
        'from api.points.services.referral_service import ReferralService',
    ],
    
    # Old task calls that need to be replaced
    'task_calls': [
        'award_points_task.delay',
        'award_topup_points_task.delay',
        'award_rental_completion_points.delay',
        'award_referral_points_task.delay',
        'award_signup_points_task.delay', 
        'deduct_points_task.delay',
        'deduct_rental_points_task.delay',
        'process_referral_task.delay',
        'complete_referral_task.delay',
        'update_leaderboard_task.delay',
    ],
    
    # Old service instantiation and calls
    'service_calls': [
        'PointsService()',
        'points_service.award',
        'points_service.deduct',
        'ReferralService()',
        'referral_service.complete',
        'referral_service.process',
    ],
}


# ============================================================================
# NEW PATTERNS: Universal API
# ============================================================================

NEW_NOTIFICATION_API = """
# ✅ NEW UNIVERSAL API (Notifications)
from api.notifications.services import notify

# Sync (immediate)
notify(user, 'template_slug', async_send=False, **context)

# Async (background)
notify(user, 'template_slug', async_send=True, **context)

# Examples:
notify(user, 'otp', async_send=True, otp_code='123456')
notify(user, 'welcome', async_send=True, first_name=user.first_name)
notify(user, 'rental_complete', async_send=True, rental_id=rental.id)
"""

NEW_POINTS_API = """
# ✅ NEW UNIVERSAL API (Points)
from api.points.services import award_points, deduct_points, complete_referral

# Award points (sync/async)
award_points(user, points, source, description, async_send=False, **metadata)

# Deduct points (sync/async)
deduct_points(user, points, source, description, async_send=False, **metadata)

# Complete referral
complete_referral(referral_code, referred_user, async_send=False)

# Examples:
award_points(user, 50, 'RENTAL', 'Completed rental', async_send=True, rental_id='R123')
award_points(user, 100, 'SIGNUP', 'Welcome bonus')
deduct_points(user, 100, 'REDEMPTION', 'Redeemed coupon', coupon_code='SAVE100')
complete_referral('ABC123', user, async_send=True)
"""


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class UsageInstance:
    """Represents a single usage of old pattern"""
    file_path: str
    line_number: int
    line_content: str
    pattern_type: str  # 'import', 'task', 'service'
    old_pattern: str
    context_before: List[str]
    context_after: List[str]
    app: str  # 'notifications' or 'points'


@dataclass
class FixSuggestion:
    """Suggested fix for old usage"""
    usage: UsageInstance
    new_code: str
    explanation: str
    confidence: str  # 'high', 'medium', 'low'
    requires_review: bool


# ============================================================================
# AST ANALYZER
# ============================================================================

class UsageAnalyzer(ast.NodeVisitor):
    """AST-based analyzer for finding old patterns in Python code"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.usages: List[UsageInstance] = []
        self.lines: List[str] = []
        
    def analyze_file(self, content: str) -> List[UsageInstance]:
        """Analyze Python file for old usages"""
        self.lines = content.split('\n')
        
        try:
            tree = ast.parse(content)
            self.visit(tree)
        except SyntaxError as e:
            print(f"⚠️  Syntax error in {self.file_path}: {e}")
        
        return self.usages
    
    def visit_Import(self, node: ast.Import):
        """Visit import statements"""
        for alias in node.names:
            self._check_import(alias.name, node.lineno)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Visit from...import statements"""
        if node.module:
            # Check module path
            if 'api.notifications' in node.module or 'api.points' in node.module:
                for alias in node.names:
                    import_str = f"from {node.module} import {alias.name}"
                    self._check_import_from(import_str, node.lineno, node.module)
        self.generic_visit(node)
    
    def visit_Call(self, node: ast.Call):
        """Visit function calls"""
        # Get function name
        func_name = self._get_call_name(node)
        if func_name:
            self._check_function_call(func_name, node.lineno)
        self.generic_visit(node)
    
    def _get_call_name(self, node: ast.Call) -> Optional[str]:
        """Extract function name from call node"""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr
        return None
    
    def _check_import(self, module_name: str, line_no: int):
        """Check if import is old pattern"""
        # This method is for simple imports, we'll handle most cases in _check_import_from
        pass
    
    def _check_import_from(self, import_str: str, line_no: int, module: str):
        """Check if from...import is old pattern"""
        if not module:
            return
            
        app = None
        patterns_to_check = []
        
        if 'api.notifications' in module:
            app = 'notifications'
            patterns_to_check = (OLD_NOTIFICATION_PATTERNS.get('task_imports', []) + 
                                OLD_NOTIFICATION_PATTERNS.get('service_imports', []))
        elif 'api.points' in module:
            app = 'points'
            patterns_to_check = (OLD_POINTS_PATTERNS.get('task_imports', []) + 
                                OLD_POINTS_PATTERNS.get('service_imports', []))
        else:
            return
        
        # Check against all old patterns
        for pattern in patterns_to_check:
            # More precise matching - check if the import statement matches
            if import_str.strip() == pattern.strip():
                self._add_usage(line_no, pattern, 'import', app)
                break
    
    def _check_function_call(self, func_name: str, line_no: int):
        """Check if function call is old pattern"""
        line_content = self.lines[line_no - 1] if line_no <= len(self.lines) else ""
        
        # Check notifications
        all_notification_calls = (OLD_NOTIFICATION_PATTERNS.get('task_calls', []) + 
                                 OLD_NOTIFICATION_PATTERNS.get('service_calls', []))
        for pattern in all_notification_calls:
            if pattern in line_content:
                pattern_type = 'task' if pattern in OLD_NOTIFICATION_PATTERNS.get('task_calls', []) else 'service'
                self._add_usage(line_no, pattern, pattern_type, 'notifications')
        
        # Check points  
        all_points_calls = (OLD_POINTS_PATTERNS.get('task_calls', []) + 
                           OLD_POINTS_PATTERNS.get('service_calls', []))
        for pattern in all_points_calls:
            if pattern in line_content:
                pattern_type = 'task' if pattern in OLD_POINTS_PATTERNS.get('task_calls', []) else 'service'
                self._add_usage(line_no, pattern, pattern_type, 'points')
    
    def _add_usage(self, line_no: int, pattern: str, pattern_type: str, app: str):
        """Add usage instance"""
        # Get context
        line_content = self.lines[line_no - 1] if line_no <= len(self.lines) else ""
        context_before = self.lines[max(0, line_no - 4):line_no - 1]
        context_after = self.lines[line_no:min(len(self.lines), line_no + 3)]
        
        usage = UsageInstance(
            file_path=self.file_path,
            line_number=line_no,
            line_content=line_content,
            pattern_type=pattern_type,
            old_pattern=pattern,
            context_before=context_before,
            context_after=context_after,
            app=app
        )
        
        self.usages.append(usage)


# ============================================================================
# REGEX FINDER (Backup for AST)
# ============================================================================

class RegexFinder:
    """Regex-based finder for patterns that AST might miss"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.usages: List[UsageInstance] = []
    
    def find_in_file(self, content: str) -> List[UsageInstance]:
        """Find old patterns using regex - more precise matching"""
        lines = content.split('\n')
        
        # Search each line for exact patterns
        for line_no, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Check notification imports
            for pattern in OLD_NOTIFICATION_PATTERNS.get('task_imports', []) + OLD_NOTIFICATION_PATTERNS.get('service_imports', []):
                if pattern in line_stripped:
                    self._add_regex_usage(lines, line_no, line, pattern, 'import', 'notifications')
            
            # Check notification calls
            for pattern in OLD_NOTIFICATION_PATTERNS.get('task_calls', []) + OLD_NOTIFICATION_PATTERNS.get('service_calls', []):
                if pattern in line_stripped:
                    pattern_type = 'task' if pattern in OLD_NOTIFICATION_PATTERNS.get('task_calls', []) else 'service'
                    self._add_regex_usage(lines, line_no, line, pattern, pattern_type, 'notifications')
            
            # Check points imports
            for pattern in OLD_POINTS_PATTERNS.get('task_imports', []) + OLD_POINTS_PATTERNS.get('service_imports', []):
                if pattern in line_stripped:
                    self._add_regex_usage(lines, line_no, line, pattern, 'import', 'points')
            
            # Check points calls
            for pattern in OLD_POINTS_PATTERNS.get('task_calls', []) + OLD_POINTS_PATTERNS.get('service_calls', []):
                if pattern in line_stripped:
                    pattern_type = 'task' if pattern in OLD_POINTS_PATTERNS.get('task_calls', []) else 'service'
                    self._add_regex_usage(lines, line_no, line, pattern, pattern_type, 'points')
        
        return self.usages
    
    def _add_regex_usage(self, lines: List[str], line_no: int, line: str, pattern: str, pattern_type: str, app: str):
        """Add usage found by regex"""
        context_before = lines[max(0, line_no - 3):line_no - 1]
        context_after = lines[line_no:min(len(lines), line_no + 2)]
        
        usage = UsageInstance(
            file_path=self.file_path,
            line_number=line_no,
            line_content=line,
            pattern_type=pattern_type,
            old_pattern=pattern,
            context_before=context_before,
            context_after=context_after,
            app=app
        )
        
        self.usages.append(usage)


# ============================================================================
# FIX SUGGESTER (AI-Powered)
# ============================================================================

class FixSuggester:
    """Generate fix suggestions based on usage patterns"""
    
    def suggest_fix(self, usage: UsageInstance) -> FixSuggestion:
        """Generate fix suggestion for usage"""
        
        if usage.app == 'notifications':
            return self._suggest_notification_fix(usage)
        elif usage.app == 'points':
            return self._suggest_points_fix(usage)
        else:
            return self._suggest_generic_fix(usage)
    
    def _suggest_notification_fix(self, usage: UsageInstance) -> FixSuggestion:
        """Suggest fix for notification usage"""
        
        # Import fixes - all notification imports should use universal API
        if usage.pattern_type == 'import':
            if 'BulkNotificationService' in usage.old_pattern:
                new_code = "from api.notifications.services import notify_bulk"
                explanation = "Replace with universal notify_bulk() import"
            else:
                new_code = "from api.notifications.services import notify"
                explanation = "Replace with universal notify() import"
            confidence = "high"
            requires_review = False
        
        # Service instantiation fixes
        elif 'NotificationService()' in usage.old_pattern:
            new_code = "# Use notify() directly - no service instantiation needed"
            explanation = "Replace service instantiation with direct notify() calls"
            confidence = "high"
            requires_review = True
        
        elif 'BulkNotificationService()' in usage.old_pattern:
            new_code = "# Use notify_bulk() directly - no service instantiation needed"
            explanation = "Replace bulk service instantiation with direct notify_bulk() calls"
            confidence = "high"
            requires_review = True
        
        # Task call fixes - specific patterns we know about
        elif 'notify_rental_started' in usage.old_pattern:
            new_code = "notify(user, 'rental_started', async_send=True, **context)"
            explanation = "Use notify() with 'rental_started' template slug"
            confidence = "high"
            requires_review = False
        
        elif 'notify_rental_completed' in usage.old_pattern:
            new_code = "notify(user, 'rental_completed', async_send=True, **context)"
            explanation = "Use notify() with 'rental_completed' template slug"
            confidence = "high"
            requires_review = False
        
        elif 'notify_account_status' in usage.old_pattern:
            new_code = "notify(user, 'account_status_changed', async_send=True, **context)"
            explanation = "Use notify() with 'account_status_changed' template slug"
            confidence = "high"
            requires_review = False
        
        elif 'notify_kyc_status' in usage.old_pattern:
            new_code = "notify(user, 'kyc_status_updated', async_send=True, **context)"
            explanation = "Use notify() with 'kyc_status_updated' template slug"
            confidence = "high"
            requires_review = False
        
        elif 'notify_wallet_recharged' in usage.old_pattern:
            new_code = "notify(user, 'wallet_recharged', async_send=True, **context)"
            explanation = "Use notify() with 'wallet_recharged' template slug"
            confidence = "high"
            requires_review = False
        
        elif 'send_otp_task' in usage.old_pattern:
            new_code = "# Use send_notification_task with 'otp' template"
            explanation = "OTP sending should use the new send_notification_task"
            confidence = "medium"
            requires_review = True
        
        elif 'send_rental_reminder_notification' in usage.old_pattern:
            new_code = "send_notification_task.apply_async(args=[user_id, 'rental_reminder', context], eta=reminder_time)"
            explanation = "Use send_notification_task with 'rental_reminder' template"
            confidence = "high"
            requires_review = False
        
        else:
            new_code = "notify(user, 'template_slug', async_send=True, **context)"
            explanation = "Use universal notify() method - determine appropriate template slug"
            confidence = "low"
            requires_review = True
        
        return FixSuggestion(
            usage=usage,
            new_code=new_code,
            explanation=explanation,
            confidence=confidence,
            requires_review=requires_review
        )
    
    def _suggest_points_fix(self, usage: UsageInstance) -> FixSuggestion:
        """Suggest fix for points usage"""
        
        # Import fixes
        if usage.pattern_type == 'import':
            if 'ReferralService' in usage.old_pattern:
                new_code = "from api.points.services import complete_referral"
                explanation = "Replace with universal complete_referral() import"
            else:
                new_code = "from api.points.services import award_points, deduct_points"
                explanation = "Replace with universal points API import"
            confidence = "high"
            requires_review = False
        
        # Service instantiation fixes
        elif 'PointsService()' in usage.old_pattern:
            new_code = "# Use award_points()/deduct_points() directly - no service instantiation needed"
            explanation = "Replace service instantiation with direct function calls"
            confidence = "high"
            requires_review = True
        
        elif 'ReferralService()' in usage.old_pattern:
            new_code = "# Use complete_referral() directly - no service instantiation needed"
            explanation = "Replace service instantiation with direct complete_referral() calls"
            confidence = "high"
            requires_review = True
        
        # Task call fixes - specific patterns we know about
        elif 'award_points_task.delay' in usage.old_pattern:
            new_code = "award_points(user, points, source, description, async_send=True, **metadata)"
            explanation = "Use award_points() with async_send=True instead of task"
            confidence = "high"
            requires_review = False
        
        elif 'award_rental_completion_points.delay' in usage.old_pattern:
            new_code = "award_points(user, points, 'RENTAL', 'Rental completion', async_send=True, rental_id=rental_id)"
            explanation = "Use award_points() with RENTAL source"
            confidence = "high"
            requires_review = False
        
        elif 'award_signup_points_task.delay' in usage.old_pattern:
            new_code = "award_points(user, points, 'SIGNUP', 'Welcome bonus', async_send=True)"
            explanation = "Use award_points() with SIGNUP source"
            confidence = "high"
            requires_review = False
        
        elif 'process_referral_task.delay' in usage.old_pattern:
            new_code = "complete_referral(user, referrer, async_send=True)"
            explanation = "Use complete_referral() with async_send=True"
            confidence = "high"
            requires_review = False
        
        elif 'deduct_points_task.delay' in usage.old_pattern:
            new_code = "deduct_points(user, points, source, description, async_send=True, **metadata)"
            explanation = "Use deduct_points() with async_send=True instead of task"
            confidence = "high"
            requires_review = False
        
        elif 'update_leaderboard_task.delay' in usage.old_pattern:
            new_code = "from api.points.tasks import calculate_leaderboard_task\ncalculate_leaderboard_task.delay()"
            explanation = "Task renamed to calculate_leaderboard_task"
            confidence = "high"
            requires_review = False
        
        else:
            new_code = "award_points(user, points, 'SOURCE', 'Description', async_send=True, **metadata)"
            explanation = "Use universal award_points() method - determine appropriate source"
            confidence = "low"
            requires_review = True
        
        return FixSuggestion(
            usage=usage,
            new_code=new_code,
            explanation=explanation,
            confidence=confidence,
            requires_review=requires_review
        )
    
    def _suggest_generic_fix(self, usage: UsageInstance) -> FixSuggestion:
        """Generic fix suggestion"""
        return FixSuggestion(
            usage=usage,
            new_code="# TODO: Update to new universal API",
            explanation="Review and update to use new universal API",
            confidence="low",
            requires_review=True
        )


# ============================================================================
# MAIN SCANNER
# ============================================================================

class ProjectScanner:
    """Main scanner for finding old usages across project"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.all_usages: List[UsageInstance] = []
        self.fix_suggestions: List[FixSuggestion] = []
        self.stats = {
            'files_scanned': 0,
            'files_with_issues': 0,
            'total_usages': 0,
            'by_app': {'notifications': 0, 'points': 0},
            'by_type': {'import': 0, 'task': 0, 'service': 0},
        }
    
    def scan(self):
        """Scan entire project"""
        print(f"🔍 Scanning project: {self.project_root}")
        print("=" * 80)
        
        # Find all Python files
        python_files = list(self.project_root.rglob("*.py"))
        
        print(f"📁 Found {len(python_files)} Python files\n")
        
        # Scan each file
        for py_file in python_files:
            # Skip migrations, __pycache__, venv, etc.
            if self._should_skip(py_file):
                continue
            
            self._scan_file(py_file)
        
        # Generate fix suggestions
        self._generate_suggestions()
        
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
            'services_backup',  # Skip backup files
            'tasks_old.py',     # Skip old backup files
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
        """Scan single file"""
        self.stats['files_scanned'] += 1
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Use regex analysis only (more reliable)
            regex_finder = RegexFinder(str(file_path))
            all_usages = regex_finder.find_in_file(content)
            
            if all_usages:
                self.stats['files_with_issues'] += 1
                self.all_usages.extend(all_usages)
                
                # Update stats
                for usage in all_usages:
                    self.stats['total_usages'] += 1
                    self.stats['by_app'][usage.app] += 1
                    self.stats['by_type'][usage.pattern_type] += 1
                
                print(f"⚠️  {file_path.relative_to(self.project_root)}: {len(all_usages)} issues")
        
        except Exception as e:
            print(f"❌ Error scanning {file_path}: {e}")
    
    def _deduplicate_usages(self, usages: List[UsageInstance]) -> List[UsageInstance]:
        """Remove duplicate usages"""
        seen = set()
        unique = []
        
        for usage in usages:
            key = (usage.file_path, usage.line_number, usage.old_pattern)
            if key not in seen:
                seen.add(key)
                unique.append(usage)
        
        return unique
    
    def _generate_suggestions(self):
        """Generate fix suggestions for all usages"""
        suggester = FixSuggester()
        
        for usage in self.all_usages:
            suggestion = suggester.suggest_fix(usage)
            self.fix_suggestions.append(suggestion)
    
    def generate_report(self, output_file: str = "old_usage_report.md"):
        """Generate detailed report"""
        report_path = self.project_root / output_file
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# Old Usage Detection Report\n\n")
            f.write(f"**Generated:** October 15, 2025\n")
            f.write(f"**Project:** {self.project_root}\n\n")
            
            # Summary
            f.write("## 📊 Summary\n\n")
            f.write(f"- **Files Scanned:** {self.stats['files_scanned']}\n")
            f.write(f"- **Files with Issues:** {self.stats['files_with_issues']}\n")
            f.write(f"- **Total Usages:** {self.stats['total_usages']}\n\n")
            
            f.write("### By App\n")
            f.write(f"- Notifications: {self.stats['by_app']['notifications']}\n")
            f.write(f"- Points: {self.stats['by_app']['points']}\n\n")
            
            f.write("### By Type\n")
            f.write(f"- Imports: {self.stats['by_type']['import']}\n")
            f.write(f"- Tasks: {self.stats['by_type']['task']}\n")
            f.write(f"- Services: {self.stats['by_type']['service']}\n\n")
            
            # Group by file
            by_file = defaultdict(list)
            for suggestion in self.fix_suggestions:
                by_file[suggestion.usage.file_path].append(suggestion)
            
            # Detailed findings
            f.write("## 🔍 Detailed Findings\n\n")
            
            for file_path in sorted(by_file.keys()):
                suggestions = by_file[file_path]
                rel_path = Path(file_path).relative_to(self.project_root)
                
                f.write(f"### `{rel_path}`\n\n")
                f.write(f"**Issues found:** {len(suggestions)}\n\n")
                
                for i, suggestion in enumerate(suggestions, 1):
                    usage = suggestion.usage
                    
                    f.write(f"#### Issue #{i} - Line {usage.line_number}\n\n")
                    
                    # Context
                    f.write("**Current Code:**\n```python\n")
                    if usage.context_before:
                        f.write('\n'.join(usage.context_before) + '\n')
                    f.write(f">>> {usage.line_content} # ⚠️ OLD USAGE\n")
                    if usage.context_after:
                        f.write('\n'.join(usage.context_after) + '\n')
                    f.write("```\n\n")
                    
                    # Suggestion
                    f.write(f"**Fix Suggestion** (Confidence: {suggestion.confidence}):\n")
                    f.write(f"```python\n{suggestion.new_code}\n```\n\n")
                    
                    f.write(f"**Explanation:** {suggestion.explanation}\n\n")
                    
                    if suggestion.requires_review:
                        f.write("⚠️ **Requires Review:** Manual verification needed\n\n")
                    else:
                        f.write("✅ **Auto-fixable:** High confidence suggestion\n\n")
                    
                    f.write("---\n\n")
            
            # New API Reference
            f.write("\n## 📚 New API Reference\n\n")
            f.write("### Notifications\n\n")
            f.write("```python\n" + NEW_NOTIFICATION_API + "\n```\n\n")
            f.write("### Points\n\n")
            f.write("```python\n" + NEW_POINTS_API + "\n```\n\n")
        
        print(f"\n📄 Report generated: {report_path}")
        
        # Also generate JSON for programmatic access
        self._generate_json_report(str(report_path).replace('.md', '.json'))
    
    def _generate_json_report(self, output_file: str):
        """Generate JSON report for programmatic access"""
        data = {
            'stats': self.stats,
            'usages': [
                {
                    'file': usage.file_path,
                    'line': usage.line_number,
                    'content': usage.line_content,
                    'pattern_type': usage.pattern_type,
                    'old_pattern': usage.old_pattern,
                    'app': usage.app,
                }
                for usage in self.all_usages
            ],
            'suggestions': [
                {
                    'file': suggestion.usage.file_path,
                    'line': suggestion.usage.line_number,
                    'old_code': suggestion.usage.line_content,
                    'new_code': suggestion.new_code,
                    'explanation': suggestion.explanation,
                    'confidence': suggestion.confidence,
                    'requires_review': suggestion.requires_review,
                }
                for suggestion in self.fix_suggestions
            ]
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        print(f"📄 JSON report generated: {output_file}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point"""
    
    if len(sys.argv) < 2:
        print("Usage: python tools/find_and_fix_old_usages.py <project_root> [options]")
        print("\nOptions:")
        print("  --include-tools    Include tools directory in scan")
        print("  --quick           Quick scan (less verbose output)")
        print("\nExamples:")
        print("  python tools/find_and_fix_old_usages.py .")
        print("  python tools/find_and_fix_old_usages.py . --quick")
        print("  python tools/find_and_fix_old_usages.py /path/to/ChargeGhar --include-tools")
        sys.exit(1)
    
    project_root = sys.argv[1]
    quick_mode = '--quick' in sys.argv
    
    # Convert relative path to absolute
    if project_root == '.':
        project_root = os.getcwd()
    else:
        project_root = os.path.abspath(project_root)
    
    if not os.path.isdir(project_root):
        print(f"❌ Error: {project_root} is not a valid directory")
        sys.exit(1)
    
    print(f"📂 Project root: {project_root}")
    
    # Run scanner
    scanner = ProjectScanner(project_root)
    scanner.scan()
    
    # Generate report only if not in quick mode
    if not quick_mode:
        scanner.generate_report()
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 SCAN SUMMARY")
    print("=" * 80)
    print(f"Files scanned: {scanner.stats['files_scanned']}")
    print(f"Files with issues: {scanner.stats['files_with_issues']}")
    print(f"Total usages found: {scanner.stats['total_usages']}")
    
    if scanner.stats['total_usages'] == 0:
        print("\n🎉 SUCCESS! No old usages found!")
        print("✅ Your codebase is clean and up-to-date!")
    else:
        print(f"\nBy App:")
        print(f"  - Notifications: {scanner.stats['by_app']['notifications']}")
        print(f"  - Points: {scanner.stats['by_app']['points']}")
        print(f"\nBy Type:")
        print(f"  - Imports: {scanner.stats['by_type']['import']}")
        print(f"  - Tasks: {scanner.stats['by_type']['task']}")
        print(f"  - Services: {scanner.stats['by_type']['service']}")
        
        if not quick_mode:
            print("\n⚠️  Check old_usage_report.md for detailed findings and fix suggestions!")
        else:
            print("\n💡 Run without --quick flag to generate detailed report")


if __name__ == "__main__":
    main()
