#!/usr/bin/env python3
"""
Celery Task Analysis Tool
Analyzes all tasks in the PowerBank application and categorizes them.
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "api.config.settings")
django.setup()

from tasks.app import app
from celery import current_app
import importlib
import inspect
from typing import Dict, List, Any

class TaskAnalyzer:
    def __init__(self):
        self.beat_schedule = app.conf.beat_schedule
        self.task_routes = app.conf.task_routes
        self.discovered_tasks = {}
        self.task_categories = {
            'automatic': [],      # Scheduled tasks (beat schedule)
            'event_driven': [],   # Triggered by events (user actions, webhooks, etc.)
            'manual': [],         # Can be called manually
            'cleanup': [],        # Maintenance/cleanup tasks
            'analytics': [],      # Reporting and analytics
            'notifications': [],  # Notification tasks
        }
        
    def discover_all_tasks(self):
        """Discover all tasks from all apps"""
        apps = [
            'api.users', 'api.stations', 'api.payments', 'api.points',
            'api.notifications', 'api.rentals', 'api.admin',
            'api.content', 'api.social', 'api.promotions', 'api.system'
        ]
        
        for app_name in apps:
            try:
                tasks_module = importlib.import_module(f"{app_name}.tasks")
                self._analyze_module_tasks(tasks_module, app_name)
            except ImportError:
                print(f"⚠️  No tasks module found for {app_name}")
                continue
    
    def _analyze_module_tasks(self, module, app_name):
        """Analyze tasks in a specific module"""
        for name, obj in inspect.getmembers(module):
            if hasattr(obj, 'delay') and hasattr(obj, 'apply_async'):
                # This is a Celery task
                task_name = f"{app_name}.tasks.{name}"
                self.discovered_tasks[task_name] = {
                    'name': name,
                    'module': app_name,
                    'full_name': task_name,
                    'function': obj,
                    'doc': obj.__doc__ or "No description",
                    'is_scheduled': self._is_scheduled_task(task_name),
                    'schedule_info': self._get_schedule_info(task_name),
                    'queue': self._get_task_queue(task_name),
                    'category': self._categorize_task(name, obj.__doc__ or "")
                }
    
    def _is_scheduled_task(self, task_name):
        """Check if task is in beat schedule"""
        for schedule_name, config in self.beat_schedule.items():
            if config['task'] == task_name:
                return True
        return False
    
    def _get_schedule_info(self, task_name):
        """Get schedule information for a task"""
        for schedule_name, config in self.beat_schedule.items():
            if config['task'] == task_name:
                schedule = config['schedule']
                if schedule == 60.0:
                    return "Every minute"
                elif schedule == 300.0:
                    return "Every 5 minutes"
                elif schedule == 900.0:
                    return "Every 15 minutes"
                elif schedule == 3600.0:
                    return "Every hour"
                elif schedule == 86400.0:
                    return "Daily"
                elif schedule == 604800.0:
                    return "Weekly"
                elif schedule == 259200.0:
                    return "Every 3 days"
                else:
                    return f"Every {schedule} seconds"
        return None
    
    def _get_task_queue(self, task_name):
        """Get the queue for a task"""
        for pattern, config in self.task_routes.items():
            if task_name.startswith(pattern.replace('*', '')):
                return config['queue']
        return 'default'
    
    def _categorize_task(self, name, doc):
        """Categorize task based on name and documentation"""
        name_lower = name.lower()
        doc_lower = doc.lower()
        
        if any(word in name_lower for word in ['cleanup', 'clean', 'expire', 'delete']):
            return 'cleanup'
        elif any(word in name_lower for word in ['analytics', 'report', 'generate', 'calculate']):
            return 'analytics'
        elif any(word in name_lower for word in ['notification', 'notify', 'send', 'alert']):
            return 'notifications'
        elif any(word in name_lower for word in ['otp', 'payment', 'points', 'rental']):
            return 'event_driven'
        else:
            return 'manual'
    
    def categorize_all_tasks(self):
        """Categorize all discovered tasks"""
        for task_name, task_info in self.discovered_tasks.items():
            category = 'automatic' if task_info['is_scheduled'] else task_info['category']
            self.task_categories[category].append(task_info)
    
    def print_analysis(self):
        """Print comprehensive task analysis"""
        print("🔍 POWERBANK CELERY TASK ANALYSIS")
        print("=" * 60)
        
        # Summary
        total_tasks = len(self.discovered_tasks)
        scheduled_tasks = sum(1 for t in self.discovered_tasks.values() if t['is_scheduled'])
        event_tasks = total_tasks - scheduled_tasks
        
        print(f"\n📊 SUMMARY:")
        print(f"   Total Tasks: {total_tasks}")
        print(f"   Automatic (Scheduled): {scheduled_tasks}")
        print(f"   Event-Driven: {event_tasks}")
        
        # Detailed breakdown
        print(f"\n🤖 AUTOMATIC TASKS (Scheduled via Beat):")
        print("-" * 50)
        
        scheduled_by_frequency = {}
        for task_info in self.task_categories['automatic']:
            freq = task_info['schedule_info']
            if freq not in scheduled_by_frequency:
                scheduled_by_frequency[freq] = []
            scheduled_by_frequency[freq].append(task_info)
        
        for frequency in ['Every minute', 'Every 5 minutes', 'Every 15 minutes', 'Every hour', 'Daily', 'Every 3 days', 'Weekly']:
            if frequency in scheduled_by_frequency:
                print(f"\n   {frequency}:")
                for task in scheduled_by_frequency[frequency]:
                    print(f"     • {task['name']} ({task['module']})")
                    print(f"       Queue: {task['queue']}")
                    print(f"       Purpose: {task['doc'][:80]}...")
        
        print(f"\n⚡ EVENT-DRIVEN TASKS (Triggered by Actions):")
        print("-" * 50)
        
        categories = ['notifications', 'event_driven', 'analytics', 'cleanup', 'manual']
        for category in categories:
            if self.task_categories[category]:
                category_name = category.replace('_', ' ').title()
                print(f"\n   {category_name}:")
                for task in self.task_categories[category]:
                    if not task['is_scheduled']:  # Only show non-scheduled tasks
                        print(f"     • {task['name']} ({task['module']})")
                        print(f"       Queue: {task['queue']}")
                        print(f"       Purpose: {task['doc'][:80]}...")
        
        print(f"\n🔄 TASK QUEUES:")
        print("-" * 50)
        
        queues = {}
        for task_info in self.discovered_tasks.values():
            queue = task_info['queue']
            if queue not in queues:
                queues[queue] = []
            queues[queue].append(task_info['name'])
        
        for queue, tasks in queues.items():
            print(f"\n   {queue.upper()} Queue ({len(tasks)} tasks):")
            for task in tasks[:5]:  # Show first 5
                print(f"     • {task}")
            if len(tasks) > 5:
                print(f"     ... and {len(tasks) - 5} more")
        
        print(f"\n📋 HOW TO MONITOR TASKS:")
        print("-" * 50)
        print("   1. View active tasks:")
        print("      docker-compose exec celery celery -A tasks.app inspect active")
        print("\n   2. View scheduled tasks:")
        print("      docker-compose exec celery celery -A tasks.app inspect scheduled")
        print("\n   3. View task stats:")
        print("      docker-compose exec celery celery -A tasks.app inspect stats")
        print("\n   4. Monitor in real-time:")
        print("      docker-compose logs -f celery")

def main():
    analyzer = TaskAnalyzer()
    analyzer.discover_all_tasks()
    analyzer.categorize_all_tasks()
    analyzer.print_analysis()

if __name__ == "__main__":
    main()