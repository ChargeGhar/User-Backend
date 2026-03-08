#!/usr/bin/env python3
"""
Task Usage Analyzer - Comprehensive Celery Task Analysis Tool
==============================================================

Analyzes Celery tasks across the entire Django project to identify:
- Task definitions and their locations
- Task usage (where tasks are called)
- Scheduled tasks in Celery Beat
- Unused tasks
- Duplicate tasks
- Inconsistencies and cleanup opportunities

Usage:
    python task_usage_analyzer.py --app <app_name> -m <method_name>
    python task_usage_analyzer.py --app <app_name> --list
    python task_usage_analyzer.py --scan-all
    python task_usage_analyzer.py --unused
    python task_usage_analyzer.py --duplicates
    python task_usage_analyzer.py --verify-beat
    python task_usage_analyzer.py --report

Author: AI Assistant
Date: 2025-01-16
"""

import argparse
import ast
import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional


@dataclass
class TaskDefinition:
    """Represents a Celery task definition"""

    name: str
    full_path: str  # e.g., api.social.tasks.recalculate_leaderboard_ranks
    app_name: str  # e.g., social
    file_path: str
    line_number: int
    decorator: str  # e.g., @shared_task, @app.task
    base_class: str  # e.g., BaseTask, NotificationTask
    docstring: Optional[str] = None
    parameters: List[str] = field(default_factory=list)


@dataclass
class TaskUsage:
    """Represents where a task is used"""

    task_name: str
    file_path: str
    line_number: int
    usage_type: str  # 'delay', 'apply_async', 'direct_call'
    context: str  # surrounding code


@dataclass
class ScheduledTask:
    """Represents a task in Celery Beat schedule"""

    schedule_name: str
    task_path: str
    schedule: str  # cron or interval
    queue: Optional[str] = None


class TaskUsageAnalyzer:
    """Main analyzer class"""

    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root or os.getcwd())
        self.api_root = self.project_root / "api"
        self.tasks_root = self.project_root / "tasks"

        self.task_definitions: Dict[str, TaskDefinition] = {}
        self.task_usages: Dict[str, List[TaskUsage]] = defaultdict(list)
        self.scheduled_tasks: Dict[str, ScheduledTask] = {}
        self.task_queues: Dict[str, str] = {}

    def scan_all(self):
        """Scan entire project for tasks"""
        print("🔍 Scanning project for Celery tasks...")
        print(f"📁 Project root: {self.project_root}")
        print(f"📁 API root: {self.api_root}")
        print()

        self._scan_task_definitions()
        self._scan_task_usages()
        self._scan_beat_schedule()
        self._scan_task_routes()

        print(f"✅ Found {len(self.task_definitions)} task definitions")
        print(
            f"✅ Found {sum(len(usages) for usages in self.task_usages.values())} task usages"
        )
        print(f"✅ Found {len(self.scheduled_tasks)} scheduled tasks")
        print()

    def _scan_task_definitions(self):
        """Scan all tasks.py files for task definitions"""
        task_files = list(self.api_root.rglob("tasks.py"))

        for task_file in task_files:
            self._parse_task_file(task_file)

    def _parse_task_file(self, file_path: Path):
        """Parse a tasks.py file for task definitions"""
        try:
            with open(file_path, "r") as f:
                content = f.read()
                tree = ast.parse(content)

            # Extract app name from path (e.g., api/social/tasks.py -> social)
            parts = file_path.parts
            api_index = parts.index("api")
            app_name = parts[api_index + 1] if api_index + 1 < len(parts) else "unknown"

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check if function has @shared_task or @app.task decorator
                    decorators = [
                        d.id
                        if isinstance(d, ast.Name)
                        else (d.func.id if isinstance(d.func, ast.Name) else None)
                        for d in node.decorator_list
                    ]

                    if any(
                        d in ["shared_task", "task", "periodic_task"]
                        for d in decorators
                        if d
                    ):
                        task_name = node.name
                        full_path = f"api.{app_name}.tasks.{task_name}"

                        # Extract decorator info
                        decorator_str = "@shared_task"
                        base_class = None
                        for dec in node.decorator_list:
                            if isinstance(dec, ast.Call):
                                # Check for base parameter
                                for keyword in dec.keywords:
                                    if keyword.arg == "base":
                                        if isinstance(keyword.value, ast.Name):
                                            base_class = keyword.value.id

                        # Extract docstring
                        docstring = ast.get_docstring(node)

                        # Extract parameters
                        params = [arg.arg for arg in node.args.args if arg.arg != "self"]

                        task_def = TaskDefinition(
                            name=task_name,
                            full_path=full_path,
                            app_name=app_name,
                            file_path=str(file_path.relative_to(self.project_root)),
                            line_number=node.lineno,
                            decorator=decorator_str,
                            base_class=base_class or "None",
                            docstring=docstring,
                            parameters=params,
                        )

                        self.task_definitions[full_path] = task_def

        except Exception as e:
            print(f"⚠️  Error parsing {file_path}: {e}")

    def _scan_task_usages(self):
        """Scan entire project for task usage (.delay(), .apply_async())"""
        python_files = list(self.api_root.rglob("*.py"))

        for py_file in python_files:
            self._find_task_calls(py_file)

    def _find_task_calls(self, file_path: Path):
        """Find all task calls in a Python file"""
        try:
            with open(file_path, "r") as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines, 1):
                # Match task.delay() or task.apply_async()
                delay_match = re.search(r"(\w+)\.delay\s*\(", line)
                async_match = re.search(r"(\w+)\.apply_async\s*\(", line)

                if delay_match or async_match:
                    task_name = (
                        delay_match.group(1) if delay_match else async_match.group(1)
                    )
                    usage_type = "delay" if delay_match else "apply_async"

                    # Try to find the full task path
                    full_task_path = self._resolve_task_path(task_name, file_path)

                    if full_task_path:
                        usage = TaskUsage(
                            task_name=full_task_path,
                            file_path=str(file_path.relative_to(self.project_root)),
                            line_number=line_num,
                            usage_type=usage_type,
                            context=line.strip(),
                        )
                        self.task_usages[full_task_path].append(usage)

        except Exception as e:
            pass  # Skip files with encoding issues

    def _resolve_task_path(self, task_name: str, file_path: Path) -> Optional[str]:
        """Try to resolve a task name to its full path"""
        # Check if it matches any known task by name
        for full_path, task_def in self.task_definitions.items():
            if task_def.name == task_name:
                return full_path
        return None

    def _scan_beat_schedule(self):
        """Scan tasks/app.py for Celery Beat schedule"""
        app_file = self.tasks_root / "app.py"

        if not app_file.exists():
            return

        try:
            with open(app_file, "r") as f:
                content = f.read()

            # Parse beat_schedule dictionary
            schedule_pattern = (
                r"'([^']+)':\s*{\s*'task':\s*'([^']+)',\s*'schedule':\s*([^,]+)"
            )
            matches = re.finditer(schedule_pattern, content)

            for match in matches:
                schedule_name = match.group(1)
                task_path = match.group(2)
                schedule = match.group(3).strip()

                scheduled_task = ScheduledTask(
                    schedule_name=schedule_name, task_path=task_path, schedule=schedule
                )

                self.scheduled_tasks[task_path] = scheduled_task

        except Exception as e:
            print(f"⚠️  Error scanning beat schedule: {e}")

    def _scan_task_routes(self):
        """Scan task routes (queue configuration)"""
        app_file = self.tasks_root / "app.py"

        if not app_file.exists():
            return

        try:
            with open(app_file, "r") as f:
                content = f.read()

            # Parse task_routes
            route_pattern = r"'([^']+)':\s*{\s*'queue':\s*'([^']+)'"
            matches = re.finditer(route_pattern, content)

            for match in matches:
                task_pattern = match.group(1)
                queue_name = match.group(2)
                self.task_queues[task_pattern] = queue_name

        except Exception as e:
            print(f"⚠️  Error scanning task routes: {e}")

    def find_unused_tasks(self) -> List[TaskDefinition]:
        """Find tasks that are defined but never used"""
        unused = []

        for full_path, task_def in self.task_definitions.items():
            # Check if task is used anywhere
            is_used = (
                full_path in self.task_usages
                or full_path in self.scheduled_tasks
                or len(self.task_usages.get(full_path, [])) > 0
            )

            if not is_used:
                unused.append(task_def)

        return unused

    def find_duplicates(self) -> Dict[str, List[TaskDefinition]]:
        """Find tasks with the same name but different paths"""
        by_name = defaultdict(list)

        for task_def in self.task_definitions.values():
            by_name[task_def.name].append(task_def)

        # Return only duplicates
        return {name: tasks for name, tasks in by_name.items() if len(tasks) > 1}

    def verify_beat_schedule(self) -> List[str]:
        """Verify all scheduled tasks exist"""
        missing = []

        for task_path in self.scheduled_tasks.keys():
            if task_path not in self.task_definitions:
                missing.append(task_path)

        return missing

    def get_app_tasks(self, app_name: str) -> List[TaskDefinition]:
        """Get all tasks for a specific app"""
        return [
            task_def
            for task_def in self.task_definitions.values()
            if task_def.app_name == app_name
        ]

    def find_task_by_method(
        self, app_name: str, method_name: str
    ) -> Optional[TaskDefinition]:
        """Find a specific task by app and method name"""
        for task_def in self.task_definitions.values():
            if task_def.app_name == app_name and task_def.name == method_name:
                return task_def
        return None

    def generate_report(self, output_file: str = None):
        """Generate comprehensive analysis report"""
        report = []
        report.append("=" * 80)
        report.append("CELERY TASK USAGE ANALYSIS REPORT")
        report.append("=" * 80)
        report.append("")

        # Summary
        report.append("📊 SUMMARY")
        report.append("-" * 80)
        report.append(f"Total Task Definitions: {len(self.task_definitions)}")
        report.append(
            f"Total Task Usages: {sum(len(usages) for usages in self.task_usages.values())}"
        )
        report.append(f"Scheduled Tasks (Beat): {len(self.scheduled_tasks)}")
        report.append(f"Unused Tasks: {len(self.find_unused_tasks())}")
        report.append(f"Duplicate Names: {len(self.find_duplicates())}")
        report.append("")

        # Tasks by app
        report.append("📦 TASKS BY APP")
        report.append("-" * 80)
        by_app = defaultdict(list)
        for task_def in self.task_definitions.values():
            by_app[task_def.app_name].append(task_def)

        for app_name in sorted(by_app.keys()):
            tasks = by_app[app_name]
            report.append(f"{app_name}: {len(tasks)} tasks")
            for task in tasks:
                usage_count = len(self.task_usages.get(task.full_path, []))
                is_scheduled = task.full_path in self.scheduled_tasks
                status = "⏰ SCHEDULED" if is_scheduled else f"📞 {usage_count} calls"
                report.append(f"  - {task.name} ({status})")
        report.append("")

        # Unused tasks
        unused = self.find_unused_tasks()
        if unused:
            report.append("❌ UNUSED TASKS (Consider removing)")
            report.append("-" * 80)
            for task_def in unused:
                report.append(f"  {task_def.full_path}")
                report.append(f"    File: {task_def.file_path}:{task_def.line_number}")
                report.append(
                    f"    Docstring: {task_def.docstring[:60] if task_def.docstring else 'None'}..."
                )
            report.append("")

        # Duplicates
        duplicates = self.find_duplicates()
        if duplicates:
            report.append("⚠️  DUPLICATE TASK NAMES")
            report.append("-" * 80)
            for name, tasks in duplicates.items():
                report.append(f"  Task name: {name}")
                for task_def in tasks:
                    report.append(f"    - {task_def.full_path} ({task_def.file_path})")
            report.append("")

        # Missing scheduled tasks
        missing = self.verify_beat_schedule()
        if missing:
            report.append("🚨 SCHEDULED TASKS NOT FOUND")
            report.append("-" * 80)
            for task_path in missing:
                report.append(f"  {task_path}")
            report.append("")

        # Task queues
        report.append("🔀 TASK QUEUE CONFIGURATION")
        report.append("-" * 80)
        for pattern, queue in self.task_queues.items():
            report.append(f"  {pattern} → {queue}")
        report.append("")

        report_text = "\n".join(report)

        if output_file:
            with open(output_file, "w") as f:
                f.write(report_text)
            print(f"✅ Report saved to {output_file}")
        else:
            print(report_text)

        return report_text


def main():
    parser = argparse.ArgumentParser(
        description="Comprehensive Celery Task Usage Analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all tasks in social app
  python task_usage_analyzer.py --app social --list

  # Find usage of specific task method
  python task_usage_analyzer.py --app social -m recalculate_leaderboard_ranks

  # Scan entire project
  python task_usage_analyzer.py --scan-all

  # Find unused tasks
  python task_usage_analyzer.py --unused

  # Find duplicate task names
  python task_usage_analyzer.py --duplicates

  # Verify beat schedule
  python task_usage_analyzer.py --verify-beat

  # Generate full report
  python task_usage_analyzer.py --report --output report.txt
        """,
    )

    parser.add_argument("--app", type=str, help="App name (e.g., social, users, rentals)")
    parser.add_argument("-m", "--method", type=str, help="Task method name")
    parser.add_argument("--list", action="store_true", help="List all tasks in app")
    parser.add_argument("--scan-all", action="store_true", help="Scan entire project")
    parser.add_argument("--unused", action="store_true", help="Find unused tasks")
    parser.add_argument(
        "--duplicates", action="store_true", help="Find duplicate task names"
    )
    parser.add_argument("--verify-beat", action="store_true", help="Verify beat schedule")
    parser.add_argument(
        "--report", action="store_true", help="Generate comprehensive report"
    )
    parser.add_argument("--output", "-o", type=str, help="Output file for report")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")

    args = parser.parse_args()

    # Initialize analyzer
    analyzer = TaskUsageAnalyzer()
    analyzer.scan_all()

    # Handle commands
    if args.app and args.list:
        # List all tasks in app
        tasks = analyzer.get_app_tasks(args.app)
        print(f"\n📋 Tasks in '{args.app}' app ({len(tasks)} total):")
        print("-" * 80)
        for task in tasks:
            usage_count = len(analyzer.task_usages.get(task.full_path, []))
            is_scheduled = task.full_path in analyzer.scheduled_tasks
            print(f"\n✓ {task.name}")
            print(f"  Path: {task.full_path}")
            print(f"  File: {task.file_path}:{task.line_number}")
            print(f"  Base: {task.base_class}")
            print(
                f"  Params: {', '.join(task.parameters) if task.parameters else 'None'}"
            )
            print(
                f"  Usage: {usage_count} calls" + (" + SCHEDULED" if is_scheduled else "")
            )
            if task.docstring:
                print(f"  Doc: {task.docstring[:100]}...")

    elif args.app and args.method:
        # Find specific task
        task = analyzer.find_task_by_method(args.app, args.method)
        if task:
            print(f"\n🔍 Found task: {task.full_path}")
            print("-" * 80)
            print(f"File: {task.file_path}:{task.line_number}")
            print(f"Base: {task.base_class}")
            print(f"Params: {', '.join(task.parameters)}")

            usages = analyzer.task_usages.get(task.full_path, [])
            print(f"\n📞 Usage: {len(usages)} calls")

            if usages:
                print("\nFound in:")
                for usage in usages:
                    print(
                        f"  • {usage.file_path}:{usage.line_number} ({usage.usage_type})"
                    )
                    print(f"    {usage.context}")

            if task.full_path in analyzer.scheduled_tasks:
                scheduled = analyzer.scheduled_tasks[task.full_path]
                print(f"\n⏰ Scheduled: {scheduled.schedule_name}")
                print(f"   Schedule: {scheduled.schedule}")
        else:
            print(f"❌ Task '{args.method}' not found in '{args.app}' app")

    elif args.unused:
        # Find unused tasks
        unused = analyzer.find_unused_tasks()
        print(f"\n❌ Unused Tasks ({len(unused)} found):")
        print("-" * 80)
        for task in unused:
            print(f"\n{task.full_path}")
            print(f"  File: {task.file_path}:{task.line_number}")
            print(f"  Recommendation: Consider removing if not needed")

    elif args.duplicates:
        # Find duplicates
        duplicates = analyzer.find_duplicates()
        if duplicates:
            print(f"\n⚠️  Duplicate Task Names ({len(duplicates)} found):")
            print("-" * 80)
            for name, tasks in duplicates.items():
                print(f"\nTask name: '{name}' appears {len(tasks)} times:")
                for task in tasks:
                    print(f"  • {task.full_path}")
                    print(f"    {task.file_path}:{task.line_number}")
        else:
            print("✅ No duplicate task names found")

    elif args.verify_beat:
        # Verify beat schedule
        missing = analyzer.verify_beat_schedule()
        if missing:
            print(f"\n🚨 Scheduled Tasks Not Found ({len(missing)}):")
            print("-" * 80)
            for task_path in missing:
                print(f"  ❌ {task_path}")
            print(
                "\nRecommendation: Remove from beat_schedule or implement missing tasks"
            )
        else:
            print("✅ All scheduled tasks exist")

    elif args.report:
        # Generate report
        analyzer.generate_report(args.output)

    elif args.scan_all:
        # Already scanned, show summary
        print("✅ Scan complete. Use --report for full analysis")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
