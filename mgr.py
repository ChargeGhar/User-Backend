#!/usr/bin/env python3
"""
PowerBank Django Deployment Manager
Beautiful menu-driven management tool for PowerBank Django deployment
"""

import os
import sys
import subprocess
import time
from datetime import datetime

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class PowerBankManager:
    def __init__(self):
        self.compose_file = "docker-compose.prod.yml"
        self.project_dir = "/opt/powerbank"
        
    def print_header(self):
        print(f"\n{Colors.CYAN}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}🚀 PowerBank Django Deployment Manager{Colors.ENDC}")
        print(f"{Colors.CYAN}{'='*60}{Colors.ENDC}")
        print(f"{Colors.YELLOW}Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.ENDC}")
        print(f"{Colors.YELLOW}Project Directory: {self.project_dir}{Colors.ENDC}")
        print(f"{Colors.CYAN}{'='*60}{Colors.ENDC}\n")

    def print_menu(self):
        menu_items = [
            ("1", "🔄 Restart Services", "Restart all PowerBank containers"),
            ("2", "⏹️  Stop Services", "Stop all PowerBank containers"),
            ("3", "🗑️  Delete All", "Stop and remove all containers, volumes, images"),
            ("4", "📊 Service Status", "Show current status of all services"),
            ("5", "📋 View Logs", "View logs for all services or specific service"),
            ("6", "🔧 Load Fixtures", "Load sample data into the database"),
            ("7", "🏥 Health Check", "Check API health and connectivity"),
            ("8", "🔄 Full Redeploy", "Complete redeployment (git pull + rebuild)"),
            ("9", "💾 Database Backup", "Create database backup"),
            ("10", "🧹 Clean Docker", "Clean unused Docker resources"),
            ("11", "🔓 Clear Port Conflicts", "Fix port conflicts (8010)"),
            ("0", "❌ Exit", "Exit the manager")
        ]
        
        print(f"{Colors.BOLD}{Colors.BLUE}Available Actions:{Colors.ENDC}\n")
        for num, title, desc in menu_items:
            print(f"{Colors.GREEN}{num:>2}.{Colors.ENDC} {Colors.BOLD}{title:<20}{Colors.ENDC} - {desc}")
        print()

    def run_command(self, command, description="", show_output=True):
        """Run a shell command with nice formatting"""
        if description:
            print(f"{Colors.BLUE}[RUNNING]{Colors.ENDC} {description}...")
        
        try:
            if show_output:
                result = subprocess.run(command, shell=True, check=True, cwd=self.project_dir)
                return result.returncode == 0
            else:
                result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True, cwd=self.project_dir)
                return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"{Colors.RED}[ERROR]{Colors.ENDC} Command failed: {e}")
            return False

    def clear_port_conflicts(self):
        """Clear any port conflicts before deployment"""
        print(f"{Colors.BLUE}🔍 Checking for port conflicts...{Colors.ENDC}")
        
        # Get API port from .env
        try:
            with open('.env', 'r') as f:
                for line in f:
                    if line.startswith('API_PORT='):
                        port = line.split('=')[1].strip()
                        break
                else:
                    port = "8010"  # default
        except:
            port = "8010"
        
        # Find containers using the port
        conflicting = self.run_command(f'docker ps --filter "publish={port}" --format "{{{{.Names}}}}"', show_output=False)
        if conflicting:
            print(f"{Colors.YELLOW}Found containers using port {port}:{Colors.ENDC}")
            for container in conflicting.split('\n'):
                if container.strip():
                    print(f"  Stopping: {container}")
                    self.run_command(f"docker stop {container}", show_output=False)
                    self.run_command(f"docker rm {container}", show_output=False)
        
        # Check for processes on port
        process_check = self.run_command(f'netstat -tlnp 2>/dev/null | grep ":{port} "', show_output=False)
        if process_check:
            print(f"{Colors.YELLOW}Port {port} is still in use, attempting to free it...{Colors.ENDC}")
            # Kill docker-proxy processes if any
            self.run_command("pkill -f docker-proxy", show_output=False)
        
        print(f"{Colors.GREEN}✅ Port conflicts cleared{Colors.ENDC}")

    def restart_services(self):
        """Restart all services"""
        print(f"\n{Colors.YELLOW}🔄 Restarting PowerBank Services...{Colors.ENDC}")
        
        # Clear port conflicts first
        self.clear_port_conflicts()
        
        # Stop and start instead of restart to avoid port issues
        self.run_command(f"docker-compose -f {self.compose_file} down", "Stopping containers")
        time.sleep(3)
        success = self.run_command(f"docker-compose -f {self.compose_file} up -d", "Starting containers")
        
        if success:
            print(f"{Colors.GREEN}✅ Services restarted successfully!{Colors.ENDC}")
            time.sleep(5)
            self.show_status()
        else:
            print(f"{Colors.RED}❌ Failed to restart services{Colors.ENDC}")

    def stop_services(self):
        """Stop all services"""
        print(f"\n{Colors.YELLOW}⏹️ Stopping PowerBank Services...{Colors.ENDC}")
        
        # Clear port conflicts to ensure clean shutdown
        self.clear_port_conflicts()
        
        success = self.run_command(f"docker-compose -f {self.compose_file} down --remove-orphans", "Stopping containers")
        if success:
            print(f"{Colors.GREEN}✅ Services stopped successfully!{Colors.ENDC}")
        else:
            print(f"{Colors.RED}❌ Failed to stop services{Colors.ENDC}")

    def delete_all(self):
        """Delete all containers, volumes, and images"""
        print(f"\n{Colors.RED}🗑️ WARNING: This will delete ALL PowerBank data!{Colors.ENDC}")
        confirm = input(f"{Colors.YELLOW}Type 'DELETE' to confirm: {Colors.ENDC}")
        
        if confirm == "DELETE":
            print(f"{Colors.RED}Deleting all PowerBank resources...{Colors.ENDC}")
            commands = [
                f"docker-compose -f {self.compose_file} down --remove-orphans --volumes",
                "docker system prune -af",
                "docker volume prune -f"
            ]
            
            for cmd in commands:
                self.run_command(cmd)
            
            print(f"{Colors.GREEN}✅ All resources deleted!{Colors.ENDC}")
        else:
            print(f"{Colors.YELLOW}❌ Deletion cancelled{Colors.ENDC}")

    def show_status(self):
        """Show service status"""
        print(f"\n{Colors.BLUE}📊 PowerBank Service Status:{Colors.ENDC}")
        self.run_command(f"docker-compose -f {self.compose_file} ps")

    def view_logs(self):
        """View logs with service selection"""
        print(f"\n{Colors.BLUE}📋 Available Services:{Colors.ENDC}")
        services = ["all", "api", "db", "redis", "rabbitmq", "celery"]
        
        for i, service in enumerate(services, 1):
            print(f"{Colors.GREEN}{i}.{Colors.ENDC} {service}")
        
        try:
            choice = int(input(f"\n{Colors.YELLOW}Select service (1-{len(services)}): {Colors.ENDC}"))
            if 1 <= choice <= len(services):
                service = services[choice - 1]
                if service == "all":
                    cmd = f"docker-compose -f {self.compose_file} logs --tail=50 -f"
                else:
                    cmd = f"docker-compose -f {self.compose_file} logs --tail=50 -f {service}"
                
                print(f"{Colors.BLUE}Showing logs for {service} (Press Ctrl+C to exit)...{Colors.ENDC}")
                self.run_command(cmd)
            else:
                print(f"{Colors.RED}Invalid choice{Colors.ENDC}")
        except (ValueError, KeyboardInterrupt):
            print(f"\n{Colors.YELLOW}Returning to menu...{Colors.ENDC}")

    def load_fixtures(self):
        """Load fixtures"""
        print(f"\n{Colors.BLUE}🔧 Loading PowerBank Fixtures...{Colors.ENDC}")
        if os.path.exists(os.path.join(self.project_dir, "load-fixtures.sh")):
            success = self.run_command("chmod +x load-fixtures.sh && ./load-fixtures.sh", "Loading fixtures")
            if success:
                print(f"{Colors.GREEN}✅ Fixtures loaded successfully!{Colors.ENDC}")
            else:
                print(f"{Colors.RED}❌ Failed to load fixtures{Colors.ENDC}")
        else:
            print(f"{Colors.RED}❌ load-fixtures.sh not found{Colors.ENDC}")

    def health_check(self):
        """Check API health"""
        print(f"\n{Colors.BLUE}🏥 Checking PowerBank API Health...{Colors.ENDC}")
        
        # Check if containers are running
        status = self.run_command(f"docker-compose -f {self.compose_file} ps --services --filter status=running", show_output=False)
        if status:
            running_services = status.split('\n') if status else []
            print(f"{Colors.GREEN}Running Services: {len(running_services)}{Colors.ENDC}")
            for service in running_services:
                print(f"  ✅ {service}")
        
        # Check API endpoint (try both with and without trailing slash)
        health_urls = [
            "http://localhost:8010/api/app/health",
            "http://localhost:8010/api/app/health/"
        ]
        
        health_passed = False
        for url in health_urls:
            health_check = self.run_command(f"curl -s -f {url}", show_output=False)
            if health_check:
                print(f"{Colors.GREEN}✅ API Health Check: PASSED{Colors.ENDC}")
                print(f"URL: {url}")
                print(f"Response: {health_check}")
                health_passed = True
                break
        
        if not health_passed:
            print(f"{Colors.RED}❌ API Health Check: FAILED{Colors.ENDC}")
            print("Tried both /api/app/health and /api/app/health/")

    def full_redeploy(self):
        """Full redeployment"""
        print(f"\n{Colors.YELLOW}🔄 Starting Full Redeployment...{Colors.ENDC}")
        confirm = input(f"{Colors.YELLOW}This will rebuild everything. Continue? (y/N): {Colors.ENDC}")
        
        if confirm.lower() == 'y':
            # Clear port conflicts before redeployment
            self.clear_port_conflicts()
            
            # Make sure script is executable
            self.run_command("chmod +x deploy-production.sh", show_output=False)
            
            success = self.run_command("./deploy-production.sh", "Running full deployment")
            if success:
                print(f"{Colors.GREEN}✅ Full redeployment completed!{Colors.ENDC}")
                time.sleep(3)
                self.show_status()
            else:
                print(f"{Colors.RED}❌ Redeployment failed{Colors.ENDC}")
        else:
            print(f"{Colors.YELLOW}❌ Redeployment cancelled{Colors.ENDC}")

    def database_backup(self):
        """Create database backup"""
        print(f"\n{Colors.BLUE}💾 Creating Database Backup...{Colors.ENDC}")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"backups/powerbank_backup_{timestamp}.sql"
        
        # Ensure backups directory exists
        os.makedirs("backups", exist_ok=True)
        
        cmd = f"docker-compose -f {self.compose_file} exec -T db pg_dump -U powerbank_user powerbank_db > {backup_file}"
        success = self.run_command(cmd, f"Creating backup: {backup_file}")
        
        if success:
            print(f"{Colors.GREEN}✅ Backup created: {backup_file}{Colors.ENDC}")
        else:
            print(f"{Colors.RED}❌ Backup failed{Colors.ENDC}")

    def clean_docker(self):
        """Clean unused Docker resources"""
        print(f"\n{Colors.BLUE}🧹 Cleaning Docker Resources...{Colors.ENDC}")
        commands = [
            "docker system prune -f",
            "docker volume prune -f",
            "docker image prune -f"
        ]
        
        for cmd in commands:
            self.run_command(cmd)
        
        print(f"{Colors.GREEN}✅ Docker cleanup completed!{Colors.ENDC}")

    def run(self):
        """Main menu loop"""
        while True:
            try:
                os.system('clear' if os.name == 'posix' else 'cls')
                self.print_header()
                self.print_menu()
                
                choice = input(f"{Colors.BOLD}Enter your choice (0-11): {Colors.ENDC}").strip()
                
                if choice == "0":
                    print(f"\n{Colors.GREEN}👋 Goodbye!{Colors.ENDC}")
                    break
                elif choice == "1":
                    self.restart_services()
                elif choice == "2":
                    self.stop_services()
                elif choice == "3":
                    self.delete_all()
                elif choice == "4":
                    self.show_status()
                elif choice == "5":
                    self.view_logs()
                elif choice == "6":
                    self.load_fixtures()
                elif choice == "7":
                    self.health_check()
                elif choice == "8":
                    self.full_redeploy()
                elif choice == "9":
                    self.database_backup()
                elif choice == "10":
                    self.clean_docker()
                elif choice == "11":
                    self.clear_port_conflicts()
                else:
                    print(f"{Colors.RED}❌ Invalid choice. Please try again.{Colors.ENDC}")
                
                if choice != "0":
                    input(f"\n{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
                    
            except KeyboardInterrupt:
                print(f"\n\n{Colors.GREEN}👋 Goodbye!{Colors.ENDC}")
                break
            except Exception as e:
                print(f"{Colors.RED}❌ An error occurred: {e}{Colors.ENDC}")
                input(f"\n{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")

if __name__ == "__main__":
    # Check if running as root
    if os.geteuid() != 0:
        print(f"{Colors.RED}❌ This script must be run as root{Colors.ENDC}")
        sys.exit(1)
    
    # Change to project directory
    project_dir = "/opt/powerbank"
    if os.path.exists(project_dir):
        os.chdir(project_dir)
    else:
        print(f"{Colors.RED}❌ Project directory {project_dir} not found{Colors.ENDC}")
        sys.exit(1)
    
    manager = PowerBankManager()
    manager.run()