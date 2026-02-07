#!/usr/bin/env python3
"""
Fix Critical Celery Beat Schedule Errors

This script automatically fixes the 7 critical errors in tasks/app.py:
1. Fix points task name mismatches
2. Fix notifications task name mismatch
3. Remove non-existent task entries

Usage:
    python3 tools/fix_beat_schedule.py --dry-run    # Preview changes
    python3 tools/fix_beat_schedule.py --fix        # Apply fixes
    python3 tools/fix_beat_schedule.py --rollback   # Restore backup

Author: ChargeGhar DevOps Team
Date: 2024-01-15
"""

import argparse
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path


class BeatScheduleFixer:
    """Fix critical beat schedule configuration errors"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.app_file = project_root / "tasks" / "app.py"
        self.backup_file = self.app_file.with_suffix(".py.backup")

    def backup(self):
        """Create backup of app.py"""
        if not self.app_file.exists():
            print(f"❌ Error: {self.app_file} not found")
            sys.exit(1)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.app_file.with_suffix(f".py.backup.{timestamp}")
        shutil.copy2(self.app_file, backup_path)
        print(f"✅ Backup created: {backup_path}")
        return backup_path

    def read_file(self) -> str:
        """Read app.py content"""
        with open(self.app_file, "r") as f:
            return f.read()

    def write_file(self, content: str):
        """Write updated content to app.py"""
        with open(self.app_file, "w") as f:
            f.write(content)

    def apply_fixes(self, content: str) -> tuple[str, list]:
        """Apply all fixes and return updated content and change log"""
        changes = []

        # Fix 1: expire-old-referrals task name
        old = "'task': 'api.points.tasks.expire_old_referrals'"
        new = "'task': 'points.expire_old_referrals'"
        if old in content:
            content = content.replace(old, new)
            changes.append("✓ Fixed expire-old-referrals task name")

        # Fix 2: cleanup-old-notifications task name
        old = "'task': 'api.notifications.tasks.cleanup_old_notifications'"
        new = "'task': 'api.notifications.tasks.cleanup_old_notifications_task'"
        if old in content:
            content = content.replace(old, new)
            changes.append("✓ Fixed cleanup-old-notifications task name")

        # Fix 3: cleanup-old-points-transactions task name
        old = "'task': 'api.points.tasks.cleanup_old_points_transactions'"
        new = "'task': 'points.cleanup_old_transactions'"
        if old in content:
            content = content.replace(old, new)
            changes.append("✓ Fixed cleanup-old-points-transactions task name")

        # Remove non-existent tasks
        tasks_to_remove = [
            "send-points-milestone-notifications",
            "generate-points-analytics",
            "calculate-monthly-leaderboard",
            "sync-user-points-balance",
        ]

        for task_name in tasks_to_remove:
            # Find and remove the entire beat schedule entry
            pattern = rf"    '{task_name}':\s*\{{[^}}]*\}},?\n"
            matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
            if matches:
                for match in matches:
                    content = content.replace(match, "")
                changes.append(f"✓ Removed non-existent task: {task_name}")

        return content, changes

    def validate_fixes(self, content: str) -> tuple[bool, list]:
        """Validate that fixes were applied correctly"""
        issues = []

        # Check that wrong task names are gone
        wrong_names = [
            "api.points.tasks.expire_old_referrals",
            "api.notifications.tasks.cleanup_old_notifications'",  # Note: without _task
            "api.points.tasks.cleanup_old_points_transactions",
            "api.points.tasks.send_points_milestone_notifications",
            "api.points.tasks.generate_points_analytics_report",
            "api.points.tasks.calculate_monthly_points_leaderboard",
            "api.points.tasks.sync_user_points_balance",
        ]

        for wrong_name in wrong_names:
            if wrong_name in content:
                issues.append(f"❌ Still contains wrong task name: {wrong_name}")

        # Check that correct names exist (for fixes, not removals)
        correct_names = [
            "points.expire_old_referrals",
            "api.notifications.tasks.cleanup_old_notifications_task",
            "points.cleanup_old_transactions",
        ]

        for correct_name in correct_names:
            if correct_name not in content:
                issues.append(f"⚠ Missing expected task name: {correct_name}")

        return len(issues) == 0, issues

    def show_diff(self, original: str, updated: str):
        """Show diff between original and updated content"""
        print("\n" + "=" * 80)
        print("CHANGES PREVIEW")
        print("=" * 80)

        original_lines = original.split("\n")
        updated_lines = updated.split("\n")

        # Simple diff - show lines that changed
        for i, (orig, upd) in enumerate(zip(original_lines, updated_lines), 1):
            if orig != upd:
                print(f"\nLine {i}:")
                print(f"  - {orig}")
                print(f"  + {upd}")

    def run_dry_run(self):
        """Preview changes without applying them"""
        print("🔍 Running dry-run (no changes will be made)...\n")

        content = self.read_file()
        updated_content, changes = self.apply_fixes(content)

        if not changes:
            print("✅ No changes needed - beat schedule is already correct!")
            return

        print("📋 Changes that would be applied:")
        for change in changes:
            print(f"  {change}")

        self.show_diff(content, updated_content)

        is_valid, issues = self.validate_fixes(updated_content)
        print("\n" + "=" * 80)
        print("VALIDATION")
        print("=" * 80)

        if is_valid:
            print("✅ All validations passed")
        else:
            print("⚠ Validation issues found:")
            for issue in issues:
                print(f"  {issue}")

        print("\n💡 To apply these changes, run:")
        print("   python3 tools/fix_beat_schedule.py --fix")

    def run_fix(self):
        """Apply fixes to beat schedule"""
        print("🔧 Applying fixes to beat schedule...\n")

        # Backup first
        backup_path = self.backup()

        # Read and fix
        content = self.read_file()
        updated_content, changes = self.apply_fixes(content)

        if not changes:
            print("✅ No changes needed - beat schedule is already correct!")
            return

        # Write changes
        self.write_file(updated_content)

        print("\n📋 Applied changes:")
        for change in changes:
            print(f"  {change}")

        # Validate
        is_valid, issues = self.validate_fixes(updated_content)
        print("\n" + "=" * 80)
        print("VALIDATION")
        print("=" * 80)

        if is_valid:
            print("✅ All validations passed")
            print(f"\n✅ Fixes applied successfully!")
            print(f"📁 Backup saved to: {backup_path}")
            print("\n🚀 Next steps:")
            print("   1. Review changes: git diff tasks/app.py")
            print(
                "   2. Test beat schedule: celery -A tasks.app beat --loglevel=info --dry-run"
            )
            print(
                "   3. Restart Celery: docker-compose restart celery celery_beat"
            )
            print("\n💡 If issues occur, rollback with:")
            print(f"   python3 tools/fix_beat_schedule.py --rollback {backup_path}")
        else:
            print("⚠ Validation issues found:")
            for issue in issues:
                print(f"  {issue}")
            print("\n⚠ Changes were applied but validation failed.")
            print(
                f"💡 Rollback with: python3 tools/fix_beat_schedule.py --rollback {backup_path}"
            )

    def run_rollback(self, backup_file: str = None):
        """Rollback to backup"""
        if backup_file:
            backup_path = Path(backup_file)
        else:
            # Find most recent backup
            backups = sorted(self.app_file.parent.glob("app.py.backup.*"), reverse=True)
            if not backups:
                print("❌ No backup files found")
                sys.exit(1)
            backup_path = backups[0]

        if not backup_path.exists():
            print(f"❌ Backup file not found: {backup_path}")
            sys.exit(1)

        print(f"🔄 Rolling back to: {backup_path}")
        shutil.copy2(backup_path, self.app_file)
        print("✅ Rollback complete")
        print("\n🚀 Restart Celery to apply changes:")
        print("   docker-compose restart celery celery_beat")


def main():
    parser = argparse.ArgumentParser(
        description="Fix critical Celery beat schedule errors",
        epilog="""
Examples:
  # Preview changes
  python3 tools/fix_beat_schedule.py --dry-run

  # Apply fixes
  python3 tools/fix_beat_schedule.py --fix

  # Rollback to backup
  python3 tools/fix_beat_schedule.py --rollback
  python3 tools/fix_beat_schedule.py --rollback tasks/app.py.backup.20240115_120000
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without applying them"
    )
    parser.add_argument("--fix", action="store_true", help="Apply fixes to beat schedule")
    parser.add_argument(
        "--rollback",
        nargs="?",
        const=True,
        metavar="BACKUP_FILE",
        help="Rollback to backup (optional: specify backup file path)",
    )

    args = parser.parse_args()

    # Determine project root
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent

    fixer = BeatScheduleFixer(project_root)

    # Require exactly one action
    actions = sum([args.dry_run, args.fix, bool(args.rollback)])
    if actions == 0:
        parser.print_help()
        sys.exit(0)
    elif actions > 1:
        print("❌ Error: Specify only one action (--dry-run, --fix, or --rollback)")
        sys.exit(1)

    # Execute action
    try:
        if args.dry_run:
            fixer.run_dry_run()
        elif args.fix:
            fixer.run_fix()
        elif args.rollback:
            backup_file = args.rollback if isinstance(args.rollback, str) else None
            fixer.run_rollback(backup_file)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
