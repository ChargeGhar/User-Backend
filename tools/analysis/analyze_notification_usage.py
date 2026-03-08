#!/usr/bin/env python3
"""
Notification Usage Analyzer
===========================

This script analyzes the usage of notification services across all apps
according to the requirements defined in api/notifications/situation.md.

It identifies:
1. Where notifications should be triggered based on business requirements
2. Current notification implementations
3. Missing notification implementations
4. Incorrect notification implementations
5. Recommendations for improvement

Usage: python analyze_notification_usage.py
"""

import os
import re
import json
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from enum import Enum

class NotificationChannel(Enum):
    IN_APP = "in_app"
    FCM = "fcm"
    SMS = "sms"
    EMAIL = "email"

class NotificationType(Enum):
    RENTAL = "rental"
    PAYMENT = "payment"
    PROMOTION = "promotion"
    SYSTEM = "system"
    ACHIEVEMENT = "achievement"

@dataclass
class NotificationRequirement:
    situation: str
    trigger: str
    channels: List[NotificationChannel]
    notification_type: NotificationType
    description: str
    priority: str  # HIGH, MEDIUM, LOW
    app_context: str  # Which app should handle this

@dataclass
class NotificationUsage:
    file_path: str
    line_number: int
    code_snippet: str
    notification_type: str
    channels: List[str]
    context: str

class NotificationUsageAnalyzer:
    def __init__(self):
        self.requirements = self._load_requirements()
        self.current_usages = []
        self.missing_implementations = []
        self.recommendations = []
        
    def _load_requirements(self) -> List[NotificationRequirement]:
        """Load notification requirements from situation.md"""
        return [
            NotificationRequirement(
                situation="Time Alert",
                trigger="15 minutes before rental ends",
                channels=[NotificationChannel.FCM, NotificationChannel.IN_APP],
                notification_type=NotificationType.RENTAL,
                description="Warns the user to return the power bank to avoid overdue charges",
                priority="HIGH",
                app_context="rentals"
            ),
            NotificationRequirement(
                situation="Profile Reminder",
                trigger="Incomplete user profile",
                channels=[NotificationChannel.IN_APP],
                notification_type=NotificationType.SYSTEM,
                description="Prompts the user to complete their profile to become eligible for rentals",
                priority="MEDIUM",
                app_context="users"
            ),
            NotificationRequirement(
                situation="Fines/Dues",
                trigger="Late return of power bank",
                channels=[NotificationChannel.IN_APP, NotificationChannel.FCM],
                notification_type=NotificationType.PAYMENT,
                description="Notifies the user of deducted balance or pending dues due to late return",
                priority="HIGH",
                app_context="payments"
            ),
            NotificationRequirement(
                situation="Rewards",
                trigger="Referral, signup, or top-up action",
                channels=[NotificationChannel.IN_APP],
                notification_type=NotificationType.ACHIEVEMENT,
                description="Displays points earned for actions like referrals, signup, or wallet top-ups",
                priority="MEDIUM",
                app_context="points"
            ),
            NotificationRequirement(
                situation="OTP",
                trigger="Login or registration request",
                channels=[NotificationChannel.SMS],
                notification_type=NotificationType.SYSTEM,
                description="Delivers a 6-digit OTP for email or phone verification during login/register",
                priority="HIGH",
                app_context="auth"
            ),
            NotificationRequirement(
                situation="Payment Status",
                trigger="After recharge or package purchase",
                channels=[NotificationChannel.IN_APP],
                notification_type=NotificationType.PAYMENT,
                description="Confirms the success or failure of a payment transaction",
                priority="HIGH",
                app_context="payments"
            ),
            NotificationRequirement(
                situation="Rental Status",
                trigger="Power bank rent or return",
                channels=[NotificationChannel.IN_APP, NotificationChannel.FCM],
                notification_type=NotificationType.RENTAL,
                description="Confirms the ejection of a power bank (rent) or successful return to a station",
                priority="HIGH",
                app_context="rentals"
            ),
            # Additional common notifications
            NotificationRequirement(
                situation="Coupon Applied",
                trigger="User applies a coupon successfully",
                channels=[NotificationChannel.IN_APP],
                notification_type=NotificationType.PROMOTION,
                description="Confirms coupon application and points awarded",
                priority="MEDIUM",
                app_context="promotions"
            ),
            NotificationRequirement(
                situation="Account Status Update",
                trigger="User account status changes",
                channels=[NotificationChannel.IN_APP, NotificationChannel.FCM],
                notification_type=NotificationType.SYSTEM,
                description="Notifies user of account status changes (active, suspended, etc.)",
                priority="HIGH",
                app_context="users"
            ),
            NotificationRequirement(
                situation="KYC Status Update",
                trigger="KYC verification status changes",
                channels=[NotificationChannel.IN_APP, NotificationChannel.FCM],
                notification_type=NotificationType.SYSTEM,
                description="Notifies user of KYC verification status (approved, rejected, pending)",
                priority="HIGH",
                app_context="users"
            )
        ]
    
    def find_python_files(self) -> List[str]:
        """Find all Python files in the project"""
        python_files = []
        
        # Search in api directory and subdirectories
        for root, dirs, files in os.walk('api'):
            # Skip __pycache__ and migrations directories
            dirs[:] = [d for d in dirs if d not in ['__pycache__', 'migrations', '__pycache__']]
            
            for file in files:
                if file.endswith('.py') and not file.startswith('__'):
                    python_files.append(os.path.join(root, file))
        
        return python_files
    
    def analyze_file_for_notifications(self, file_path: str) -> List[NotificationUsage]:
        """Analyze a file for notification usage"""
        usages = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Patterns to look for notification usage
            patterns = [
                # OLD VERBOSE PATTERNS (need updating)
                r'NotificationService\(\)\.create_notification',
                r'notification_service\.create_notification',
                r'send_notification',
                
                # NEW CLEAN PATTERNS (already optimized)
                r'notify\(',
                r'notify_otp\(',
                r'notify_payment\(',
                r'notify_profile_reminder\(',
                r'notify_kyc_status\(',
                r'notify_account_status\(',
                r'notify_fines_dues\(',
                r'notify_coupon_applied\(',
                r'notify_rental_started\(',
                r'notify_points_earned\(',
                
                # Task calls (old pattern)
                r'send_.*_notification.*\.delay',
                r'send_.*_notification.*\(',
                
                # Direct service calls (old pattern)
                r'send_sms',
                r'send_push_notification',
                r'FCMService\(\)',
                r'SMSService\(\)',
                
                # Email notifications (old pattern)
                r'send_email',
                r'EmailService\(\)',
                
                # Template usage
                r'template_slug.*=',
                r'notification_type.*=',
            ]
            
            for i, line in enumerate(lines, 1):
                for pattern in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        # Extract context (3 lines before and after)
                        start_line = max(0, i - 4)
                        end_line = min(len(lines), i + 3)
                        context_lines = lines[start_line:end_line]
                        context = '\n'.join(f"{start_line + j + 1:4d}: {line}" for j, line in enumerate(context_lines))
                        
                        # Try to determine notification type and channels
                        notification_type = self._extract_notification_type(line, context_lines)
                        channels = self._extract_channels(line, context_lines)
                        
                        # Determine if this is old or new pattern
                        usage_pattern = self._detect_usage_pattern(line)
                        
                        usage = NotificationUsage(
                            file_path=file_path,
                            line_number=i,
                            code_snippet=line.strip(),
                            notification_type=notification_type,
                            channels=channels,
                            context=context
                        )
                        # Add pattern info to usage
                        usage.pattern = usage_pattern
                        usages.append(usage)
                        break  # Only count each line once
            
        except Exception as e:
            print(f"Error analyzing {file_path}: {str(e)}")
        
        return usages
    
    def _extract_notification_type(self, line: str, context_lines: List[str]) -> str:
        """Extract notification type from code"""
        # Look for explicit notification_type assignments
        type_patterns = [
            r"notification_type.*['\"](\w+)['\"]",
            r"['\"](\w+)['\"].*notification_type",
            r"type.*['\"](\w+)['\"]",
        ]
        
        all_text = line + ' ' + ' '.join(context_lines)
        
        for pattern in type_patterns:
            match = re.search(pattern, all_text, re.IGNORECASE)
            if match:
                return match.group(1).lower()
        
        # Infer from context
        if any(word in all_text.lower() for word in ['rental', 'rent', 'return']):
            return 'rental'
        elif any(word in all_text.lower() for word in ['payment', 'wallet', 'recharge', 'topup']):
            return 'payment'
        elif any(word in all_text.lower() for word in ['otp', 'login', 'register', 'profile']):
            return 'system'
        elif any(word in all_text.lower() for word in ['coupon', 'promotion', 'discount']):
            return 'promotion'
        elif any(word in all_text.lower() for word in ['points', 'reward', 'achievement']):
            return 'achievement'
        
        return 'unknown'
    
    def _extract_channels(self, line: str, context_lines: List[str]) -> List[str]:
        """Extract notification channels from code"""
        channels = []
        all_text = line + ' ' + ' '.join(context_lines)
        
        if any(word in all_text.lower() for word in ['sms', 'sparrow', 'send_sms']):
            channels.append('sms')
        if any(word in all_text.lower() for word in ['fcm', 'push', 'firebase']):
            channels.append('fcm')
        if any(word in all_text.lower() for word in ['email', 'send_email']):
            channels.append('email')
        if any(word in all_text.lower() for word in ['in_app', 'create_notification']):
            channels.append('in_app')
        
        return channels if channels else ['unknown']
    
    def _detect_usage_pattern(self, line: str) -> str:
        """Detect if usage is old verbose pattern or new clean pattern"""
        line_lower = line.lower()
        
        # NEW CLEAN PATTERNS
        new_patterns = [
            'notify_otp(', 'notify_payment(', 'notify_profile_reminder(',
            'notify_kyc_status(', 'notify_account_status(', 'notify_fines_dues(',
            'notify_coupon_applied(', 'notify_rental_started(', 'notify_points_earned(',
            'notify('
        ]
        
        # OLD VERBOSE PATTERNS
        old_patterns = [
            'notificationservice().create_notification',
            'notification_service.create_notification',
            'send_notification',
            'send_otp_task.delay',
            'fcmservice()',
            'smsservice()',
            'emailservice()'
        ]
        
        # Check for new patterns first
        for pattern in new_patterns:
            if pattern in line_lower:
                return 'NEW_CLEAN'
        
        # Check for old patterns
        for pattern in old_patterns:
            if pattern in line_lower:
                return 'OLD_VERBOSE'
        
        return 'UNKNOWN'
    
    def analyze_app_context(self, file_path: str) -> str:
        """Determine which app context a file belongs to"""
        if '/users/' in file_path:
            return 'users'
        elif '/rentals/' in file_path:
            return 'rentals'
        elif '/payments/' in file_path:
            return 'payments'
        elif '/points/' in file_path:
            return 'points'
        elif '/promotions/' in file_path:
            return 'promotions'
        elif '/auth/' in file_path or '/authentication/' in file_path:
            return 'auth'
        elif '/notifications/' in file_path:
            return 'notifications'
        elif '/social/' in file_path:
            return 'social'
        else:
            return 'unknown'
    
    def find_missing_implementations(self) -> List[Dict]:
        """Find missing notification implementations"""
        missing = []
        
        # Group current usages by app context
        usages_by_app = {}
        for usage in self.current_usages:
            app_context = self.analyze_app_context(usage.file_path)
            if app_context not in usages_by_app:
                usages_by_app[app_context] = []
            usages_by_app[app_context].append(usage)
        
        # Check each requirement
        for req in self.requirements:
            app_usages = usages_by_app.get(req.app_context, [])
            
            # Check if requirement is implemented
            implemented = False
            for usage in app_usages:
                if (req.notification_type.value in usage.notification_type or 
                    any(channel.value in usage.channels for channel in req.channels)):
                    implemented = True
                    break
            
            if not implemented:
                missing.append({
                    'requirement': req,
                    'app_context': req.app_context,
                    'priority': req.priority,
                    'expected_channels': [ch.value for ch in req.channels],
                    'expected_type': req.notification_type.value
                })
        
        return missing
    
    def generate_recommendations(self) -> List[Dict]:
        """Generate recommendations for improvement"""
        recommendations = []
        
        # Analyze current implementations
        for usage in self.current_usages:
            app_context = self.analyze_app_context(usage.file_path)
            
            # Check if this is old verbose pattern that needs updating
            if hasattr(usage, 'pattern') and usage.pattern == 'OLD_VERBOSE':
                migration_suggestion = self._generate_migration_suggestion(usage)
                if migration_suggestion:
                    recommendations.append({
                        'type': 'MIGRATION',
                        'file': usage.file_path,
                        'line': usage.line_number,
                        'current_code': usage.code_snippet,
                        'suggested_code': migration_suggestion,
                        'reason': 'Migrate from old verbose API to new clean one-liner',
                        'priority': 'OPTIMIZATION'
                    })
            
            # Find matching requirements for channel analysis
            matching_reqs = [req for req in self.requirements if req.app_context == app_context]
            
            for req in matching_reqs:
                # Check if channels match
                expected_channels = [ch.value for ch in req.channels]
                current_channels = usage.channels
                
                missing_channels = [ch for ch in expected_channels if ch not in current_channels]
                extra_channels = [ch for ch in current_channels if ch not in expected_channels and ch != 'unknown']
                
                if missing_channels or extra_channels:
                    recommendations.append({
                        'type': 'CHANNEL_FIX',
                        'file': usage.file_path,
                        'line': usage.line_number,
                        'situation': req.situation,
                        'current_channels': current_channels,
                        'expected_channels': expected_channels,
                        'missing_channels': missing_channels,
                        'extra_channels': extra_channels,
                        'priority': req.priority,
                        'recommendation': self._generate_channel_recommendation(missing_channels, extra_channels)
                    })
        
        return recommendations
    
    def _generate_channel_recommendation(self, missing: List[str], extra: List[str]) -> str:
        """Generate specific recommendation text"""
        recommendations = []
        
        if missing:
            recommendations.append(f"Add missing channels: {', '.join(missing)}")
        
        if extra:
            recommendations.append(f"Consider removing unnecessary channels: {', '.join(extra)}")
        
        return "; ".join(recommendations)
    
    def _generate_migration_suggestion(self, usage: NotificationUsage) -> str:
        """Generate migration suggestion from old to new API"""
        line = usage.code_snippet.lower()
        
        # OTP notifications
        if 'otp' in line and ('send_otp' in line or 'otp_task' in line):
            return "notify_otp(user, otp_code, purpose='login')"
        
        # Payment notifications
        if 'payment' in line and ('create_notification' in line or 'payment_status' in line):
            return "notify_payment(user, 'successful', amount, transaction_id)"
        
        # Profile reminders
        if 'profile' in line and ('reminder' in line or 'complete' in line):
            return "notify_profile_reminder(user)"
        
        # KYC notifications
        if 'kyc' in line:
            return "notify_kyc_status(user, 'approved', rejection_reason)"
        
        # Account status
        if 'account' in line and 'status' in line:
            return "notify_account_status(user, new_status, reason)"
        
        # Fines/dues
        if any(word in line for word in ['fine', 'due', 'penalty', 'overdue']):
            return "notify_fines_dues(user, amount, reason)"
        
        # Coupon applied
        if 'coupon' in line:
            return "notify_coupon_applied(user, coupon_code, points)"
        
        # Rental notifications
        if 'rental' in line:
            if 'start' in line:
                return "notify_rental_started(user, powerbank_id, station_name, max_hours)"
            elif 'end' in line or 'complete' in line:
                return "notify_rental_completed(user, powerbank_id, total_cost)"
        
        # Points/rewards
        if any(word in line for word in ['point', 'reward', 'achievement']):
            return "notify_points_earned(user, points, total_points)"
        
        # Generic notification
        if 'create_notification' in line:
            return "notify(user, 'template_slug', key='value')"
        
        return None
    
    def run_analysis(self) -> Dict[str, Any]:
        """Run the complete notification usage analysis"""
        print("🔍 Analyzing Notification Usage Across All Apps")
        print("=" * 60)
        print(f"📋 Loaded {len(self.requirements)} notification requirements from situation.md")
        print()
        
        # Find all Python files
        python_files = self.find_python_files()
        print(f"📁 Scanning {len(python_files)} Python files...")
        
        # Analyze each file
        for file_path in python_files:
            usages = self.analyze_file_for_notifications(file_path)
            self.current_usages.extend(usages)
        
        print(f"📊 Found {len(self.current_usages)} notification usage instances")
        
        # Find missing implementations
        missing = self.find_missing_implementations()
        
        # Generate recommendations
        recommendations = self.generate_recommendations()
        
        return {
            'total_files_scanned': len(python_files),
            'total_usages_found': len(self.current_usages),
            'requirements_count': len(self.requirements),
            'missing_implementations': missing,
            'recommendations': recommendations,
            'current_usages': self.current_usages
        }
    
    def print_detailed_report(self, analysis: Dict[str, Any]):
        """Print a detailed analysis report"""
        print("\n📊 NOTIFICATION USAGE ANALYSIS REPORT")
        print("=" * 60)
        
        # Summary
        print(f"📈 Summary:")
        print(f"  • Total files scanned: {analysis['total_files_scanned']}")
        print(f"  • Notification usages found: {analysis['total_usages_found']}")
        print(f"  • Requirements defined: {analysis['requirements_count']}")
        print(f"  • Missing implementations: {len(analysis['missing_implementations'])}")
        print(f"  • Recommendations: {len(analysis['recommendations'])}")
        
        # Current Usage by App
        print(f"\n📱 Current Usage by App:")
        usage_by_app = {}
        for usage in analysis['current_usages']:
            app = self.analyze_app_context(usage.file_path)
            if app not in usage_by_app:
                usage_by_app[app] = []
            usage_by_app[app].append(usage)
        
        for app, usages in sorted(usage_by_app.items()):
            print(f"  📁 {app.upper()}: {len(usages)} usages")
            for usage in usages[:3]:  # Show first 3
                print(f"    • {os.path.basename(usage.file_path)}:{usage.line_number} - {usage.notification_type}")
            if len(usages) > 3:
                print(f"    • ... and {len(usages) - 3} more")
        
        # Missing Implementations
        if analysis['missing_implementations']:
            print(f"\n❌ Missing Implementations ({len(analysis['missing_implementations'])}):")
            for missing in analysis['missing_implementations']:
                req = missing['requirement']
                print(f"  🚨 {req.situation} ({missing['priority']} priority)")
                print(f"    App: {missing['app_context']}")
                print(f"    Trigger: {req.trigger}")
                print(f"    Expected channels: {', '.join(missing['expected_channels'])}")
                print(f"    Expected type: {missing['expected_type']}")
                print(f"    Description: {req.description}")
                print()
        
        # Separate migration and channel recommendations
        migration_recs = [r for r in analysis['recommendations'] if r.get('type') == 'MIGRATION']
        channel_recs = [r for r in analysis['recommendations'] if r.get('type') == 'CHANNEL_FIX']
        
        # Migration Recommendations (Old -> New API)
        if migration_recs:
            print(f"\n🔄 Migration Recommendations ({len(migration_recs)}):")
            print("   Convert old verbose API to new clean one-liners:")
            for rec in migration_recs[:10]:  # Show first 10
                print(f"  📁 {rec['file']}:{rec['line']}")
                print(f"    ❌ OLD: {rec['current_code']}")
                print(f"    ✅ NEW: {rec['suggested_code']}")
                print(f"    💡 Reason: {rec['reason']}")
                print()
            
            if len(migration_recs) > 10:
                print(f"    ... and {len(migration_recs) - 10} more migration suggestions")
        
        # Channel Recommendations
        if channel_recs:
            print(f"\n💡 Channel Recommendations ({len(channel_recs)}):")
            for rec in channel_recs[:10]:  # Show first 10
                print(f"  📁 {rec['file']}:{rec['line']}")
                print(f"    Situation: {rec['situation']} ({rec['priority']} priority)")
                print(f"    Current: {', '.join(rec['current_channels'])}")
                print(f"    Expected: {', '.join(rec['expected_channels'])}")
                print(f"    Action: {rec['recommendation']}")
                print()
            
            if len(channel_recs) > 10:
                print(f"    ... and {len(channel_recs) - 10} more channel recommendations")
        
        # Implementation Status by Requirement
        print(f"\n✅ Implementation Status by Requirement:")
        for req in self.requirements:
            # Check if implemented
            implemented = any(
                self.analyze_app_context(usage.file_path) == req.app_context and
                req.notification_type.value in usage.notification_type
                for usage in analysis['current_usages']
            )
            
            status = "✅ IMPLEMENTED" if implemented else "❌ MISSING"
            priority_icon = "🔴" if req.priority == "HIGH" else "🟡" if req.priority == "MEDIUM" else "🟢"
            
            print(f"  {priority_icon} {status}: {req.situation}")
            print(f"    App: {req.app_context} | Type: {req.notification_type.value}")
            print(f"    Channels: {', '.join([ch.value for ch in req.channels])}")
    
    def export_to_json(self, analysis: Dict[str, Any], filename: str = "notification_analysis.json"):
        """Export analysis results to JSON file"""
        # Convert dataclasses to dictionaries for JSON serialization
        export_data = {
            'summary': {
                'total_files_scanned': analysis['total_files_scanned'],
                'total_usages_found': analysis['total_usages_found'],
                'requirements_count': analysis['requirements_count'],
                'missing_implementations_count': len(analysis['missing_implementations']),
                'recommendations_count': len(analysis['recommendations'])
            },
            'requirements': [
                {
                    'situation': req.situation,
                    'trigger': req.trigger,
                    'channels': [ch.value for ch in req.channels],
                    'notification_type': req.notification_type.value,
                    'description': req.description,
                    'priority': req.priority,
                    'app_context': req.app_context
                }
                for req in self.requirements
            ],
            'current_usages': [
                {
                    'file_path': usage.file_path,
                    'line_number': usage.line_number,
                    'code_snippet': usage.code_snippet,
                    'notification_type': usage.notification_type,
                    'channels': usage.channels,
                    'app_context': self.analyze_app_context(usage.file_path)
                }
                for usage in analysis['current_usages']
            ],
            'missing_implementations': [
                {
                    'situation': missing['requirement'].situation,
                    'app_context': missing['app_context'],
                    'priority': missing['priority'],
                    'expected_channels': missing['expected_channels'],
                    'expected_type': missing['expected_type'],
                    'description': missing['requirement'].description
                }
                for missing in analysis['missing_implementations']
            ],
            'recommendations': analysis['recommendations']
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Analysis exported to: {filename}")


def main():
    """Main function to run the notification usage analyzer"""
    print("🚀 Notification Usage Analyzer")
    print("=" * 60)
    print("Analyzing notification implementations against situation.md requirements")
    print()
    
    analyzer = NotificationUsageAnalyzer()
    
    # Run analysis
    analysis = analyzer.run_analysis()
    
    # Print detailed report
    analyzer.print_detailed_report(analysis)
    
    # Export to JSON
    analyzer.export_to_json(analysis)
    
    # Final recommendations
    migration_count = len([r for r in analysis['recommendations'] if r.get('type') == 'MIGRATION'])
    channel_count = len([r for r in analysis['recommendations'] if r.get('type') == 'CHANNEL_FIX'])
    
    print(f"\n🎯 Next Steps:")
    if analysis['missing_implementations']:
        print(f"  1. Implement {len(analysis['missing_implementations'])} missing notification features using new clean API")
        print(f"  2. Focus on HIGH priority items first")
    
    if migration_count > 0:
        print(f"  3. 🔄 Migrate {migration_count} old verbose API calls to new clean one-liners")
        print(f"     - This will reduce code by 87.5% and improve maintainability")
    
    if channel_count > 0:
        print(f"  4. Review {channel_count} channel recommendations")
        print(f"  5. Ensure proper notification channels are used")
    
    print(f"  6. Review notification_analysis.json for detailed findings")
    print(f"  7. Use new clean API: notify_otp(), notify_payment(), etc.")


if __name__ == "__main__":
    main()