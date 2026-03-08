#!/usr/bin/env python3
"""
Celery Task Monitoring Script
Monitor active, scheduled, and failed tasks in real-time
"""

import subprocess
import json
import time
from datetime import datetime

def run_celery_command(command):
    """Run celery command and return output"""
    try:
        result = subprocess.run(
            f"docker-compose exec -T celery celery -A tasks.app {command}",
            shell=True,
            capture_output=True,
            text=True
        )
        return result.stdout
    except Exception as e:
        return f"Error: {e}"

def monitor_tasks():
    """Monitor Celery tasks"""
    print("🔍 CELERY TASK MONITOR")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Active tasks
    print("\n🏃 ACTIVE TASKS:")
    print("-" * 30)
    active = run_celery_command("inspect active")
    if "empty" in active.lower() or not active.strip():
        print("   No active tasks")
    else:
        print(active)
    
    # Scheduled tasks
    print("\n⏰ SCHEDULED TASKS:")
    print("-" * 30)
    scheduled = run_celery_command("inspect scheduled")
    if "empty" in scheduled.lower() or not scheduled.strip():
        print("   No scheduled tasks")
    else:
        print(scheduled)
    
    # Worker stats
    print("\n📊 WORKER STATS:")
    print("-" * 30)
    stats = run_celery_command("inspect stats")
    print(stats)
    
    # Reserved tasks
    print("\n📋 RESERVED TASKS:")
    print("-" * 30)
    reserved = run_celery_command("inspect reserved")
    if "empty" in reserved.lower() or not reserved.strip():
        print("   No reserved tasks")
    else:
        print(reserved)

def show_task_routes():
    """Show task routing information"""
    print("\n🔄 TASK ROUTING:")
    print("-" * 30)
    routes = run_celery_command("inspect registered")
    print(routes)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--routes":
        show_task_routes()
    elif len(sys.argv) > 1 and sys.argv[1] == "--watch":
        # Continuous monitoring
        try:
            while True:
                monitor_tasks()
                print("\n" + "="*60)
                print("Refreshing in 10 seconds... (Ctrl+C to stop)")
                time.sleep(10)
        except KeyboardInterrupt:
            print("\nMonitoring stopped.")
    else:
        monitor_tasks()