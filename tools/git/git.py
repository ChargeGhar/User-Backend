#!/usr/bin/env python3
"""
GitHub Branch Manager - A comprehensive tool for managing Git branches
Features:
- List all local and remote branches
- Interactive branch switching and pulling
- Show detailed diff before pulling
- Categorize changed, new, and deleted files
- Stash management
- Conflict detection and resolution helpers
- Branch comparison
- Commit history viewing
"""

import subprocess
import sys
import os
from typing import List, Tuple, Dict
from enum import Enum


class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class FileStatus(Enum):
    """File change status types"""
    MODIFIED = "Modified"
    ADDED = "Added"
    DELETED = "Deleted"
    RENAMED = "Renamed"


class GitManager:
    """Main Git management class"""
    
    def __init__(self):
        self.current_branch = None
        self.repo_path = None
        self._verify_git_repo()
    
    def _verify_git_repo(self):
        """Verify we're in a git repository"""
        try:
            result = self._run_command("git rev-parse --show-toplevel")
            self.repo_path = result.strip()
            result = self._run_command("git rev-parse --abbrev-ref HEAD")
            self.current_branch = result.strip()
        except subprocess.CalledProcessError:
            print(f"{Colors.RED}❌ Error: Not a git repository{Colors.ENDC}")
            sys.exit(1)
    
    def _run_command(self, command: str, check=True) -> str:
        """Execute shell command and return output"""
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            check=check
        )
        return result.stdout
    
    def _run_command_with_status(self, command: str) -> Tuple[str, int]:
        """Execute command and return output with status code"""
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True
        )
        return result.stdout, result.returncode
    
    def print_header(self, text: str):
        """Print formatted header"""
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.CYAN}{text.center(70)}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.ENDC}\n")
    
    def print_section(self, text: str):
        """Print section header"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}▶ {text}{Colors.ENDC}")
        print(f"{Colors.BLUE}{'-'*70}{Colors.ENDC}")
    
    def get_all_branches(self) -> Dict[str, List[str]]:
        """Get all local and remote branches"""
        local_branches = []
        remote_branches = []
        
        # Get local branches
        output = self._run_command("git branch")
        for line in output.split('\n'):
            if line.strip():
                branch = line.strip().replace('* ', '')
                local_branches.append(branch)
        
        # Get remote branches
        output = self._run_command("git branch -r")
        for line in output.split('\n'):
            if line.strip() and 'HEAD' not in line:
                branch = line.strip()
                remote_branches.append(branch)
        
        return {
            'local': local_branches,
            'remote': remote_branches
        }
    
    def display_branches(self):
        """Display all branches with formatting"""
        self.print_header("GIT BRANCHES")
        branches = self.get_all_branches()
        
        # Display current branch
        print(f"{Colors.GREEN}📍 Current Branch: {Colors.BOLD}{self.current_branch}{Colors.ENDC}\n")
        
        # Display local branches
        self.print_section("Local Branches")
        for i, branch in enumerate(branches['local'], 1):
            marker = "➜" if branch == self.current_branch else " "
            color = Colors.GREEN if branch == self.current_branch else Colors.YELLOW
            print(f"{color}{marker} [{i}] {branch}{Colors.ENDC}")
        
        # Display remote branches
        self.print_section("Remote Branches")
        for i, branch in enumerate(branches['remote'], 1):
            print(f"{Colors.CYAN}  [{i}] {branch}{Colors.ENDC}")
    
    def get_file_changes(self, target_branch: str) -> Dict[str, List[str]]:
        """Get categorized file changes between current branch and target"""
        changes = {
            'modified': [],
            'added': [],
            'deleted': [],
            'renamed': []
        }
        
        # Fetch latest changes
        self._run_command(f"git fetch origin {target_branch}", check=False)
        
        # Get diff summary
        output = self._run_command(
            f"git diff --name-status {self.current_branch}..origin/{target_branch}"
        )
        
        for line in output.split('\n'):
            if not line.strip():
                continue
            
            parts = line.split('\t')
            status = parts[0][0]
            
            if status == 'M':
                changes['modified'].append(parts[1])
            elif status == 'A':
                changes['added'].append(parts[1])
            elif status == 'D':
                changes['deleted'].append(parts[1])
            elif status == 'R':
                changes['renamed'].append(f"{parts[1]} -> {parts[2]}")
        
        return changes
    
    def display_file_changes(self, changes: Dict[str, List[str]]):
        """Display categorized file changes"""
        total = sum(len(files) for files in changes.values())
        
        if total == 0:
            print(f"{Colors.GREEN}✓ No changes detected. Branch is up to date!{Colors.ENDC}")
            return False
        
        print(f"\n{Colors.BOLD}📊 Total Changes: {total} files{Colors.ENDC}\n")
        
        if changes['modified']:
            print(f"{Colors.YELLOW}📝 Modified Files ({len(changes['modified'])}){Colors.ENDC}")
            for file in changes['modified']:
                print(f"   {Colors.YELLOW}M{Colors.ENDC}  {file}")
        
        if changes['added']:
            print(f"\n{Colors.GREEN}➕ New Files ({len(changes['added'])}){Colors.ENDC}")
            for file in changes['added']:
                print(f"   {Colors.GREEN}A{Colors.ENDC}  {file}")
        
        if changes['deleted']:
            print(f"\n{Colors.RED}🗑️  Deleted Files ({len(changes['deleted'])}){Colors.ENDC}")
            for file in changes['deleted']:
                print(f"   {Colors.RED}D{Colors.ENDC}  {file}")
        
        if changes['renamed']:
            print(f"\n{Colors.CYAN}↪️  Renamed Files ({len(changes['renamed'])}){Colors.ENDC}")
            for file in changes['renamed']:
                print(f"   {Colors.CYAN}R{Colors.ENDC}  {file}")
        
        return True
    
    def show_file_diff(self, filename: str, target_branch: str):
        """Show detailed diff for a specific file"""
        print(f"\n{Colors.BOLD}{'─'*70}{Colors.ENDC}")
        print(f"{Colors.BOLD}📄 Diff for: {filename}{Colors.ENDC}")
        print(f"{Colors.BOLD}{'─'*70}{Colors.ENDC}\n")
        
        # Show colored diff
        diff_output = self._run_command(
            f"git diff {self.current_branch}..origin/{target_branch} -- {filename}"
        )
        
        for line in diff_output.split('\n'):
            if line.startswith('+') and not line.startswith('+++'):
                print(f"{Colors.GREEN}{line}{Colors.ENDC}")
            elif line.startswith('-') and not line.startswith('---'):
                print(f"{Colors.RED}{line}{Colors.ENDC}")
            elif line.startswith('@@'):
                print(f"{Colors.CYAN}{line}{Colors.ENDC}")
            else:
                print(line)
    
    def review_modified_files(self, modified_files: List[str], target_branch: str) -> bool:
        """Review each modified file and get user confirmation"""
        if not modified_files:
            return True
        
        print(f"\n{Colors.BOLD}🔍 Reviewing Modified Files{Colors.ENDC}")
        print("You can review the changes before pulling.\n")
        
        for i, file in enumerate(modified_files, 1):
            print(f"\n{Colors.YELLOW}[{i}/{len(modified_files)}] {file}{Colors.ENDC}")
            
            while True:
                choice = input(f"View diff? (y=yes, s=skip, q=quit review): ").lower().strip()
                
                if choice == 'y':
                    self.show_file_diff(file, target_branch)
                    break
                elif choice == 's':
                    print(f"{Colors.CYAN}⏭️  Skipped{Colors.ENDC}")
                    break
                elif choice == 'q':
                    print(f"{Colors.BLUE}Exiting review...{Colors.ENDC}")
                    return True
                else:
                    print(f"{Colors.RED}Invalid choice. Please enter y, s, or q{Colors.ENDC}")
        
        return True
    
    def check_local_changes(self) -> bool:
        """Check if there are uncommitted local changes"""
        output = self._run_command("git status --porcelain")
        return len(output.strip()) > 0
    
    def stash_changes(self):
        """Stash current changes"""
        print(f"{Colors.YELLOW}💾 Stashing local changes...{Colors.ENDC}")
        self._run_command("git stash save 'Auto-stash before pull'")
        print(f"{Colors.GREEN}✓ Changes stashed successfully{Colors.ENDC}")
    
    def pull_branch(self, branch_name: str):
        """Pull changes from specified branch"""
        self.print_header(f"PULLING FROM: {branch_name}")
        
        # Get changes first
        changes = self.get_file_changes(branch_name)
        has_changes = self.display_file_changes(changes)
        
        if not has_changes:
            return
        
        # Review modified files
        if changes['modified']:
            print(f"\n{Colors.BOLD}Do you want to review the modified files?{Colors.ENDC}")
            review = input("Review diffs? (y/n): ").lower().strip()
            
            if review == 'y':
                self.review_modified_files(changes['modified'], branch_name)
        
        # Final confirmation
        print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}")
        print(f"{Colors.BOLD}Ready to pull changes from: {Colors.GREEN}{branch_name}{Colors.ENDC}")
        confirm = input(f"{Colors.BOLD}Proceed with pull? (y/n): {Colors.ENDC}").lower().strip()
        
        if confirm != 'y':
            print(f"{Colors.RED}❌ Pull cancelled{Colors.ENDC}")
            return
        
        # Check for local changes
        if self.check_local_changes():
            print(f"\n{Colors.YELLOW}⚠️  You have uncommitted local changes{Colors.ENDC}")
            stash = input("Stash changes before pulling? (y/n): ").lower().strip()
            
            if stash == 'y':
                self.stash_changes()
            else:
                print(f"{Colors.RED}❌ Cannot pull with uncommitted changes{Colors.ENDC}")
                return
        
        # Perform the pull
        print(f"\n{Colors.CYAN}🔄 Pulling changes...{Colors.ENDC}")
        output, status = self._run_command_with_status(f"git pull origin {branch_name}")
        
        if status == 0:
            print(f"{Colors.GREEN}✅ Successfully pulled from {branch_name}!{Colors.ENDC}")
            print(output)
        else:
            print(f"{Colors.RED}❌ Pull failed with conflicts{Colors.ENDC}")
            print(output)
            self.show_conflict_help()
    
    def show_conflict_help(self):
        """Show help for resolving conflicts"""
        print(f"\n{Colors.YELLOW}🔧 Conflict Resolution Help:{Colors.ENDC}")
        print(f"1. Run: {Colors.CYAN}git status{Colors.ENDC} to see conflicted files")
        print(f"2. Edit conflicted files manually")
        print(f"3. Run: {Colors.CYAN}git add <file>{Colors.ENDC} after resolving")
        print(f"4. Run: {Colors.CYAN}git commit{Colors.ENDC} to complete the merge")
    
    def compare_branches(self, branch1: str, branch2: str):
        """Compare two branches"""
        self.print_header(f"COMPARING: {branch1} vs {branch2}")
        
        # Commits in branch2 not in branch1
        output = self._run_command(f"git log --oneline {branch1}..{branch2}")
        commits_ahead = output.strip().split('\n') if output.strip() else []
        
        # Commits in branch1 not in branch2
        output = self._run_command(f"git log --oneline {branch2}..{branch1}")
        commits_behind = output.strip().split('\n') if output.strip() else []
        
        print(f"{Colors.GREEN}📈 {branch2} is ahead by {len(commits_ahead)} commit(s){Colors.ENDC}")
        if commits_ahead and commits_ahead[0]:
            for commit in commits_ahead[:5]:
                print(f"   {commit}")
            if len(commits_ahead) > 5:
                print(f"   ... and {len(commits_ahead) - 5} more")
        
        print(f"\n{Colors.YELLOW}📉 {branch2} is behind by {len(commits_behind)} commit(s){Colors.ENDC}")
        if commits_behind and commits_behind[0]:
            for commit in commits_behind[:5]:
                print(f"   {commit}")
            if len(commits_behind) > 5:
                print(f"   ... and {len(commits_behind) - 5} more")
    
    def show_recent_commits(self, count: int = 10):
        """Show recent commits"""
        self.print_header("RECENT COMMITS")
        output = self._run_command(f"git log --oneline -n {count} --decorate --color=always")
        print(output)
    
    def switch_branch(self, branch_name: str):
        """Switch to a different branch"""
        if self.check_local_changes():
            print(f"{Colors.YELLOW}⚠️  You have uncommitted changes{Colors.ENDC}")
            action = input("(s)tash, (c)ommit, or (a)bort? ").lower().strip()
            
            if action == 's':
                self.stash_changes()
            elif action == 'c':
                print("Please commit your changes manually and try again")
                return
            else:
                print(f"{Colors.RED}❌ Branch switch cancelled{Colors.ENDC}")
                return
        
        print(f"{Colors.CYAN}🔄 Switching to {branch_name}...{Colors.ENDC}")
        output, status = self._run_command_with_status(f"git checkout {branch_name}")
        
        if status == 0:
            self.current_branch = branch_name
            print(f"{Colors.GREEN}✅ Switched to {branch_name}{Colors.ENDC}")
        else:
            print(f"{Colors.RED}❌ Failed to switch branch{Colors.ENDC}")
            print(output)
    """
    Add these methods to your GitManager class.
    Make sure they are indented with 4 spaces (one indentation level) 
    to be inside the class.

    Place them AFTER the switch_branch method and BEFORE the main() function.
    """

    def delete_branch(self, branch_input: str, force: bool = False):
        """Delete a local branch"""
        # Check if input is a number (list index)
        if branch_input.strip().isdigit():
            branches = self.get_all_branches()
            index = int(branch_input.strip()) - 1
            if 0 <= index < len(branches['local']):
                branch_name = branches['local'][index]
            else:
                print(f"{Colors.RED}❌ Invalid branch number. You have {len(branches['local'])} local branches.{Colors.ENDC}")
                return
        else:
            branch_name = branch_input.strip()
            
        if branch_name == self.current_branch:
            print(f"{Colors.RED}❌ Cannot delete the current branch{Colors.ENDC}")
            return
        
        flag = "-D" if force else "-d"
        print(f"{Colors.YELLOW}🗑️  Deleting branch: {branch_name}...{Colors.ENDC}")
        
        output, status = self._run_command_with_status(f"git branch {flag} {branch_name}")
        
        if status == 0:
            print(f"{Colors.GREEN}✅ Branch '{branch_name}' deleted successfully{Colors.ENDC}")
        else:
            print(f"{Colors.RED}❌ Failed to delete branch{Colors.ENDC}")
            print(output)
            if not force:
                print(f"\n{Colors.YELLOW}Tip: Use force delete if branch has unmerged changes{Colors.ENDC}")

    def delete_remote_branch(self, branch_input: str):
        """Delete a remote branch"""
        # Check if input is a number (list index)
        if branch_input.strip().isdigit():
            branches = self.get_all_branches()
            index = int(branch_input.strip()) - 1
            if 0 <= index < len(branches['remote']):
                branch_name = branches['remote'][index]
            else:
                print(f"{Colors.RED}❌ Invalid branch number. You have {len(branches['remote'])} remote branches.{Colors.ENDC}")
                return
        else:
            branch_name = branch_input.strip()
        
        # Remove 'origin/' prefix if present
        branch_name = branch_name.replace('origin/', '')
        
        print(f"{Colors.YELLOW}⚠️  WARNING: This will delete the remote branch '{branch_name}'!{Colors.ENDC}")
        confirm = input(f"Type 'DELETE' to confirm: ").strip()
        
        if confirm != 'DELETE':
            print(f"{Colors.RED}❌ Deletion cancelled{Colors.ENDC}")
            return
        
        output, status = self._run_command_with_status(f"git push origin --delete {branch_name}")
        
        if status == 0:
            print(f"{Colors.GREEN}✅ Remote branch '{branch_name}' deleted successfully{Colors.ENDC}")
        else:
            print(f"{Colors.RED}❌ Failed to delete remote branch{Colors.ENDC}")
            print(output)

    def create_branch(self, branch_name: str, from_branch: str = None):
        """Create a new branch"""
        if from_branch:
            command = f"git checkout -b {branch_name} {from_branch}"
            print(f"{Colors.CYAN}🌿 Creating branch '{branch_name}' from '{from_branch}'...{Colors.ENDC}")
        else:
            command = f"git checkout -b {branch_name}"
            print(f"{Colors.CYAN}🌿 Creating new branch '{branch_name}'...{Colors.ENDC}")
        
        output, status = self._run_command_with_status(command)
        
        if status == 0:
            self.current_branch = branch_name
            print(f"{Colors.GREEN}✅ Branch created and switched to '{branch_name}'{Colors.ENDC}")
        else:
            print(f"{Colors.RED}❌ Failed to create branch{Colors.ENDC}")
            print(output)

    def rename_branch(self, old_name: str, new_name: str):
        """Rename a branch"""
        if old_name == self.current_branch:
            command = f"git branch -m {new_name}"
            print(f"{Colors.CYAN}✏️  Renaming current branch to '{new_name}'...{Colors.ENDC}")
        else:
            command = f"git branch -m {old_name} {new_name}"
            print(f"{Colors.CYAN}✏️  Renaming '{old_name}' to '{new_name}'...{Colors.ENDC}")
        
        output, status = self._run_command_with_status(command)
        
        if status == 0:
            if old_name == self.current_branch:
                self.current_branch = new_name
            print(f"{Colors.GREEN}✅ Branch renamed successfully{Colors.ENDC}")
        else:
            print(f"{Colors.RED}❌ Failed to rename branch{Colors.ENDC}")
            print(output)

    def push_current_branch(self, set_upstream: bool = False):
        """Push current branch to remote"""
        if set_upstream:
            command = f"git push -u origin {self.current_branch}"
            print(f"{Colors.CYAN}📤 Pushing and setting upstream for '{self.current_branch}'...{Colors.ENDC}")
        else:
            command = f"git push origin {self.current_branch}"
            print(f"{Colors.CYAN}📤 Pushing '{self.current_branch}' to remote...{Colors.ENDC}")
        
        output, status = self._run_command_with_status(command)
        
        if status == 0:
            print(f"{Colors.GREEN}✅ Branch pushed successfully{Colors.ENDC}")
        else:
            print(f"{Colors.RED}❌ Push failed{Colors.ENDC}")
            print(output)

    def merge_branch(self, branch_name: str):
        """Merge a branch into current branch"""
        print(f"{Colors.CYAN}🔀 Merging '{branch_name}' into '{self.current_branch}'...{Colors.ENDC}")
        
        confirm = input(f"Proceed with merge? (y/n): ").lower().strip()
        if confirm != 'y':
            print(f"{Colors.RED}❌ Merge cancelled{Colors.ENDC}")
            return
        
        output, status = self._run_command_with_status(f"git merge {branch_name}")
        
        if status == 0:
            print(f"{Colors.GREEN}✅ Successfully merged '{branch_name}'{Colors.ENDC}")
            print(output)
        else:
            print(f"{Colors.RED}❌ Merge failed with conflicts{Colors.ENDC}")
            print(output)
            self.show_conflict_help()

    def fetch_all(self):
        """Fetch all remote branches"""
        print(f"{Colors.CYAN}📡 Fetching all remote branches...{Colors.ENDC}")
        output, status = self._run_command_with_status("git fetch --all --prune")
        
        if status == 0:
            print(f"{Colors.GREEN}✅ Fetch completed{Colors.ENDC}")
        else:
            print(f"{Colors.RED}❌ Fetch failed{Colors.ENDC}")
        print(output)

    def prune_branches(self):
        """Remove tracking branches that no longer exist on remote"""
        print(f"{Colors.YELLOW}🧹 Pruning deleted remote branches...{Colors.ENDC}")
        output = self._run_command("git remote prune origin")
        print(output)
        print(f"{Colors.GREEN}✅ Pruning completed{Colors.ENDC}")

    def show_stash_list(self):
        """Show all stashed changes"""
        self.print_header("STASH LIST")
        output = self._run_command("git stash list")
        if output.strip():
            print(output)
        else:
            print(f"{Colors.YELLOW}No stashes found{Colors.ENDC}")

    def apply_stash(self, stash_id: str = "0"):
        """Apply a stashed change"""
        print(f"{Colors.CYAN}📦 Applying stash...{Colors.ENDC}")
        output, status = self._run_command_with_status(f"git stash apply stash@{{{stash_id}}}")
        
        if status == 0:
            print(f"{Colors.GREEN}✅ Stash applied successfully{Colors.ENDC}")
        else:
            print(f"{Colors.RED}❌ Failed to apply stash{Colors.ENDC}")
            print(output)


# NOTE: After the GitManager class ends, add this main() function at the module level (no indentation):

def main():
    """Main program loop"""
    git = GitManager()
    
    while True:
        git.print_header("GIT BRANCH MANAGER")
        print(f"{Colors.GREEN}Current Branch: {Colors.BOLD}{git.current_branch}{Colors.ENDC}")
        print(f"{Colors.CYAN}Repository: {git.repo_path}{Colors.ENDC}\n")
        
        # Grid Menu Display
        print(f"{Colors.BOLD}{'─'*70}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.CYAN}🎯 BRANCH OPERATIONS{Colors.ENDC}")
        print(f"{Colors.BOLD}{'─'*70}{Colors.ENDC}")
        print(f"  {Colors.YELLOW}1.{Colors.ENDC} List Branches    {Colors.YELLOW}2.{Colors.ENDC} Create Branch    {Colors.YELLOW}3.{Colors.ENDC} Switch Branch")
        print(f"  {Colors.YELLOW}4.{Colors.ENDC} Delete Local     {Colors.YELLOW}5.{Colors.ENDC} Delete Remote    {Colors.YELLOW}6.{Colors.ENDC} Rename Branch")
        
        print(f"\n{Colors.BOLD}{Colors.BLUE}📊 SYNC & COMPARE{Colors.ENDC}")
        print(f"{Colors.BOLD}{'─'*70}{Colors.ENDC}")
        print(f"  {Colors.YELLOW}7.{Colors.ENDC} Pull + Review    {Colors.YELLOW}8.{Colors.ENDC} Push Branch      {Colors.YELLOW}9.{Colors.ENDC} Fetch All")
        print(f"  {Colors.YELLOW}10.{Colors.ENDC} Merge Branch    {Colors.YELLOW}11.{Colors.ENDC} Compare Branches")
        
        print(f"\n{Colors.BOLD}{Colors.GREEN}📜 HISTORY & INFO{Colors.ENDC}")
        print(f"{Colors.BOLD}{'─'*70}{Colors.ENDC}")
        print(f"  {Colors.YELLOW}12.{Colors.ENDC} Recent Commits  {Colors.YELLOW}13.{Colors.ENDC} Git Status")
        
        print(f"\n{Colors.BOLD}{Colors.GREEN}💾 STASH{Colors.ENDC}                 {Colors.BOLD}{Colors.CYAN}🔧 MAINTENANCE{Colors.ENDC}")
        print(f"{Colors.BOLD}{'─'*70}{Colors.ENDC}")
        print(f"  {Colors.YELLOW}14.{Colors.ENDC} Stash List      {Colors.YELLOW}15.{Colors.ENDC} Apply Stash      {Colors.YELLOW}16.{Colors.ENDC} Prune Branches")
        print(f"  {Colors.YELLOW}17.{Colors.ENDC} Refresh Info")
        
        print(f"\n{Colors.BOLD}{'─'*70}{Colors.ENDC}")
        print(f"  {Colors.RED}0.{Colors.ENDC} Exit")
        print(f"{Colors.BOLD}{'─'*70}{Colors.ENDC}")
        
        choice = input(f"\n{Colors.BOLD}➤ Enter choice: {Colors.ENDC}").strip()
        
        if choice == '1':
            git.display_branches()
            input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.ENDC}")
        
        elif choice == '2':
            branch_name = input(f"{Colors.BOLD}Enter new branch name: {Colors.ENDC}").strip()
            from_branch = input(f"Create from branch (leave empty for current): ").strip()
            if branch_name:
                git.create_branch(branch_name, from_branch if from_branch else None)
            input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.ENDC}")
        
        elif choice == '3':
            git.display_branches()
            branch = input(f"\n{Colors.BOLD}Enter branch name to switch to: {Colors.ENDC}").strip()
            if branch:
                git.switch_branch(branch)
            input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.ENDC}")
        
        elif choice == '4':
            git.display_branches()
            branch = input(f"\n{Colors.BOLD}Enter branch name/number to delete: {Colors.ENDC}").strip()
            if branch:
                force = input("Force delete (unmerged changes)? (y/n): ").lower().strip() == 'y'
                git.delete_branch(branch, force)
            input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.ENDC}")
        
        elif choice == '5':
            git.display_branches()
            branch = input(f"\n{Colors.BOLD}Enter remote branch name/number to delete: {Colors.ENDC}").strip()
            if branch:
                git.delete_remote_branch(branch)
            input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.ENDC}")
        
        elif choice == '6':
            git.display_branches()
            old_name = input(f"\n{Colors.BOLD}Branch to rename (leave empty for current): {Colors.ENDC}").strip()
            new_name = input(f"{Colors.BOLD}New branch name: {Colors.ENDC}").strip()
            if new_name:
                git.rename_branch(old_name if old_name else git.current_branch, new_name)
            input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.ENDC}")
        
        elif choice == '7':
            branch = input(f"{Colors.BOLD}Enter branch name to pull from: {Colors.ENDC}").strip()
            if branch:
                git.pull_branch(branch)
            input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.ENDC}")
        
        elif choice == '8':
            upstream = input("Set upstream tracking? (y/n): ").lower().strip() == 'y'
            git.push_current_branch(upstream)
            input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.ENDC}")
        
        elif choice == '9':
            git.fetch_all()
            input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.ENDC}")
        
        elif choice == '10':
            git.display_branches()
            branch = input(f"\n{Colors.BOLD}Branch to merge into current: {Colors.ENDC}").strip()
            if branch:
                git.merge_branch(branch)
            input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.ENDC}")
        
        elif choice == '11':
            git.display_branches()
            branch1 = input(f"\n{Colors.BOLD}Enter first branch: {Colors.ENDC}").strip()
            branch2 = input(f"{Colors.BOLD}Enter second branch: {Colors.ENDC}").strip()
            if branch1 and branch2:
                git.compare_branches(branch1, branch2)
            input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.ENDC}")
        
        elif choice == '12':
            count = input(f"Number of commits to show (default 10): ").strip()
            count = int(count) if count.isdigit() else 10
            git.show_recent_commits(count)
            input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.ENDC}")
        
        elif choice == '13':
            git.print_header("GIT STATUS")
            output = git._run_command("git status")
            print(output)
            input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.ENDC}")
        
        elif choice == '14':
            git.show_stash_list()
            input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.ENDC}")
        
        elif choice == '15':
            git.show_stash_list()
            stash_id = input(f"\nStash number to apply (default 0): ").strip()
            git.apply_stash(stash_id if stash_id else "0")
            input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.ENDC}")
        
        elif choice == '16':
            git.prune_branches()
            input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.ENDC}")
        
        elif choice == '17':
            git._verify_git_repo()
            print(f"{Colors.GREEN}✅ Branch info refreshed{Colors.ENDC}")
            input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.ENDC}")
        
        elif choice == '0':
            print(f"\n{Colors.GREEN}👋 Thank you for using Git Branch Manager!{Colors.ENDC}\n")
            sys.exit(0)
        
        else:
            print(f"{Colors.RED}❌ Invalid choice. Please try again.{Colors.ENDC}")
            input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.ENDC}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}👋 Goodbye!{Colors.ENDC}\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.RED}❌ Error: {str(e)}{Colors.ENDC}\n")
        sys.exit(1)