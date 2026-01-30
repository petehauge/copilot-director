#!/usr/bin/env python3
"""
Script to copy source code and issues from one GitHub repository to another
without using fork or branch operations.

Source: https://github.com/gim-home/JediMaster-TerraformSample
Destination: Current repository (phauge-UnifiedGatewayWithJediMaster)
"""

import os
import sys
import subprocess
import json
import shutil
import argparse
from pathlib import Path
from typing import List, Dict, Any
import requests
from datetime import datetime


def get_github_token_from_cli() -> str | None:
    """
    Try to get GitHub token from the GitHub CLI (gh).
    
    Returns:
        GitHub token if available, None otherwise
    """
    try:
        result = subprocess.run(
            ['gh', 'auth', 'token'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        # gh CLI not installed or timed out
        pass
    return None


class RepoContentCopier:
    def __init__(self, source_repo: str, dest_repo: str, github_token: str):
        """
        Initialize the repository content copier.
        
        Args:
            source_repo: Source repository in format 'owner/repo'
            dest_repo: Destination repository in format 'owner/repo'
            github_token: GitHub personal access token for API access
        """
        self.source_repo = source_repo
        self.dest_repo = dest_repo
        self.github_token = github_token
        
        self.source_owner, self.source_name = source_repo.split('/')
        self.dest_owner, self.dest_name = dest_repo.split('/')
        
        self.headers = {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
    
    def validate_token(self) -> bool:
        """
        Validate the GitHub token by making a test API call.
        
        Returns:
            True if token is valid, False otherwise
        """
        print("Validating GitHub token...")
        url = "https://api.github.com/user"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            user_data = response.json()
            print(f"✓ Authenticated as: {user_data.get('login', 'Unknown')}")
            return True
        else:
            print(f"✗ Token validation failed: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
    
    def check_dest_repo_empty(self) -> tuple[bool, List[str]]:
        """
        Check if the destination repository is empty (only contains allowed files).
        
        Allowed files/folders that don't count as "content":
        - .github/
        - .gitignore
        - README.md, README.txt, README (any case)
        - LICENSE, LICENSE.md, LICENSE.txt (any case)
        - CODEOWNERS
        - CONTRIBUTING.md
        - CODE_OF_CONDUCT.md
        - SECURITY.md
        
        Returns:
            Tuple of (is_empty, list_of_unexpected_files)
        """
        print(f"\nChecking if destination repository is empty: {self.dest_repo}")
        
        url = f"https://api.github.com/repos/{self.dest_repo}/contents"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 404:
            # Empty repo with no commits returns 404
            print("✓ Destination repository is empty (no commits yet)")
            return True, []
        
        if response.status_code != 200:
            print(f"✗ Failed to check destination repository: {response.status_code}")
            print(f"  Response: {response.text}")
            return False, []
        
        contents = response.json()
        
        # Define allowed files/folders (case-insensitive for some)
        allowed_exact = {'.github', '.gitignore', 'codeowners', 'contributing.md', 
                        'code_of_conduct.md', 'security.md'}
        allowed_prefixes = ['readme', 'license']
        
        unexpected_files = []
        
        for item in contents:
            name = item['name']
            name_lower = name.lower()
            
            # Check if it's an allowed file
            if name_lower in allowed_exact:
                continue
            
            # Check if it starts with an allowed prefix
            if any(name_lower.startswith(prefix) for prefix in allowed_prefixes):
                continue
            
            # This file is not allowed
            unexpected_files.append(name)
        
        if unexpected_files:
            print(f"✗ Destination repository contains unexpected files:")
            for f in unexpected_files:
                print(f"  - {f}")
            return False, unexpected_files
        else:
            print("✓ Destination repository is empty (only contains allowed files)")
            return True, []
        
    def run_command(self, cmd: List[str], cwd: str = None) -> subprocess.CompletedProcess:
        """Run a shell command and return the result."""
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"Error: {result.stderr}")
            raise Exception(f"Command failed: {' '.join(cmd)}")
        
        return result
    
    def copy_source_code(self):
        """
        Copy source code from the source repository to the destination repository.
        
        Clones both repos to temp directories, copies files from source to dest,
        then commits and pushes to the destination.
        """
        print("\n" + "="*60)
        print("COPYING SOURCE CODE")
        print("="*60)
        
        # Create temporary directories for cloning
        temp_base = Path(os.getcwd()) / '.temp_repo_copy'
        source_dir = temp_base / 'source'
        dest_dir = temp_base / 'dest'
        
        # Clean up temp directory if it exists from previous run
        if temp_base.exists():
            print(f"Cleaning up existing temporary directory...")
            shutil.rmtree(temp_base, ignore_errors=True)
        
        temp_base.mkdir(parents=True, exist_ok=True)
        
        try:
            # Clone the source repository
            print(f"\nCloning source repository: {self.source_repo}")
            source_url = f"https://github.com/{self.source_repo}.git"
            self.run_command(['git', 'clone', source_url, str(source_dir)])
            
            # Clone the destination repository with authentication
            print(f"\nCloning destination repository: {self.dest_repo}")
            dest_url = f"https://{self.github_token}@github.com/{self.dest_repo}.git"
            self.run_command(['git', 'clone', dest_url, str(dest_dir)])
            
            # Copy files from source to destination (exclude .git directory)
            print("\nCopying files from source to destination...")
            
            files_copied = 0
            dirs_created = 0
            
            for item in source_dir.rglob('*'):
                # Skip .git directory
                if '.git' in item.parts:
                    continue
                
                # Calculate relative path
                rel_path = item.relative_to(source_dir)
                dest_item = dest_dir / rel_path
                
                if item.is_dir():
                    # Create directory
                    dest_item.mkdir(parents=True, exist_ok=True)
                    dirs_created += 1
                else:
                    # Copy file
                    dest_item.parent.mkdir(parents=True, exist_ok=True)
                    dest_item.write_bytes(item.read_bytes())
                    files_copied += 1
                    print(f"  Copied: {rel_path}")
            
            print(f"\n✓ Created {dirs_created} directories")
            print(f"✓ Copied {files_copied} files")
            
            # Stage, commit, and push changes to destination
            print("\nCommitting and pushing changes to destination repository...")
            
            # Configure git user for the commit
            self.run_command(['git', 'config', 'user.email', 'copilot@github.com'], cwd=str(dest_dir))
            self.run_command(['git', 'config', 'user.name', 'GitHub Copilot'], cwd=str(dest_dir))
            
            # Stage all changes
            self.run_command(['git', 'add', '.'], cwd=str(dest_dir))
            
            # Check if there are changes to commit
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=str(dest_dir),
                capture_output=True,
                text=True
            )
            
            if result.stdout.strip():
                # Commit the changes
                commit_msg = f"Copy content from {self.source_repo}"
                self.run_command(['git', 'commit', '-m', commit_msg], cwd=str(dest_dir))
                
                # Push to remote
                self.run_command(['git', 'push', 'origin', 'HEAD'], cwd=str(dest_dir))
                print("\n✓ Changes pushed to destination repository")
            else:
                print("\n✓ No changes to commit (destination already up to date)")
            
        finally:
            # Clean up temporary directories
            if temp_base.exists():
                print(f"\nCleaning up temporary directories...")
                shutil.rmtree(temp_base, ignore_errors=True)
    
    def get_issues(self, include_closed: bool = False) -> List[Dict[str, Any]]:
        """Fetch issues from the source repository.
        
        Args:
            include_closed: If True, include closed issues. Default is False (open issues only).
        """
        state = 'all' if include_closed else 'open'
        print(f"\nFetching {'all' if include_closed else 'open'} issues from {self.source_repo}...")
        
        issues = []
        page = 1
        per_page = 100
        
        while True:
            url = f"https://api.github.com/repos/{self.source_repo}/issues"
            params = {
                'state': state,
                'page': page,
                'per_page': per_page,
                'filter': 'all'
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code != 200:
                print(f"Error fetching issues: {response.status_code}")
                print(f"Response: {response.text}")
                break
            
            page_issues = response.json()
            
            if not page_issues:
                break
            
            # Filter out pull requests (they appear in issues API)
            page_issues = [issue for issue in page_issues if 'pull_request' not in issue]
            issues.extend(page_issues)
            
            print(f"  Fetched page {page}: {len(page_issues)} items")
            
            if len(page_issues) < per_page:
                break
            
            page += 1
        
        print(f"✓ Found {len(issues)} issues to copy")
        return issues
    
    def create_issue(self, issue_data: Dict[str, Any]) -> bool:
        """
        Create an issue in the destination repository.
        
        Args:
            issue_data: Issue data from source repository
            
        Returns:
            True if successful, False otherwise
        """
        url = f"https://api.github.com/repos/{self.dest_repo}/issues"
        
        # Prepare issue body with metadata
        original_number = issue_data['number']
        original_url = issue_data['html_url']
        original_author = issue_data['user']['login']
        original_created = issue_data['created_at']
        original_state = issue_data['state']
        
        body = f"*Originally created as issue #{original_number} by @{original_author} on {original_created}*\n"
        body += f"*Original URL: {original_url}*\n\n"
        body += "---\n\n"
        body += issue_data['body'] or "(No description provided)"
        
        # Prepare labels
        labels = [label['name'] for label in issue_data.get('labels', [])]
        
        new_issue = {
            'title': issue_data['title'],
            'body': body,
            'labels': labels
        }
        
        response = requests.post(url, headers=self.headers, json=new_issue)
        
        if response.status_code == 201:
            new_issue_data = response.json()
            print(f"  ✓ Created issue #{new_issue_data['number']}: {issue_data['title']}")
            
            # Close the issue if it was closed in the source
            if original_state == 'closed':
                self.close_issue(new_issue_data['number'])
            
            return True
        else:
            print(f"  ✗ Failed to create issue: {issue_data['title']}")
            print(f"    Status: {response.status_code}")
            print(f"    Response: {response.text}")
            return False
    
    def close_issue(self, issue_number: int):
        """Close an issue in the destination repository."""
        url = f"https://api.github.com/repos/{self.dest_repo}/issues/{issue_number}"
        data = {'state': 'closed'}
        
        response = requests.patch(url, headers=self.headers, json=data)
        
        if response.status_code == 200:
            print(f"    ✓ Closed issue #{issue_number}")
        else:
            print(f"    ✗ Failed to close issue #{issue_number}")
    
    def copy_issues(self, include_closed: bool = False):
        """Copy issues from source to destination repository.
        
        Args:
            include_closed: If True, include closed issues. Default is False (open issues only).
        """
        print("\n" + "="*60)
        print("COPYING ISSUES" + (" (including closed)" if include_closed else " (open only)"))
        print("="*60)
        
        issues = self.get_issues(include_closed=include_closed)
        
        if not issues:
            print("No issues to copy.")
            return
        
        print(f"\nCreating {len(issues)} issues in {self.dest_repo}...")
        
        success_count = 0
        failed_count = 0
        
        for issue in issues:
            if self.create_issue(issue):
                success_count += 1
            else:
                failed_count += 1
        
        print(f"\n✓ Successfully created {success_count} issues")
        if failed_count > 0:
            print(f"✗ Failed to create {failed_count} issues")
    
    def copy_all(self, force: bool = False, include_closed_issues: bool = False):
        """
        Copy both source code and issues.
        
        Args:
            force: If True, skip the empty destination check and copy anyway
            include_closed_issues: If True, copy closed issues as well. Default is False.
        """
        print("\n" + "="*60)
        print("REPOSITORY CONTENT COPY")
        print(f"Source: {self.source_repo}")
        print(f"Destination: {self.dest_repo}")
        print("="*60)
        
        # Validate token before starting any operations
        if not self.validate_token():
            print("\n✗ Cannot proceed without a valid GitHub token.")
            print("Please provide a valid token using --token or GITHUB_TOKEN environment variable.")
            sys.exit(1)
        
        # Check if destination repo is empty (unless force is specified)
        if not force:
            is_empty, unexpected_files = self.check_dest_repo_empty()
            if not is_empty:
                print("\n✗ Destination repository is not empty!")
                print("  To copy anyway, use the --force flag.")
                sys.exit(1)
        else:
            print("\n⚠ Force flag set - skipping empty destination check")
        
        # Copy source code
        self.copy_source_code()
        
        # Copy issues
        self.copy_issues(include_closed=include_closed_issues)
        
        print("\n" + "="*60)
        print("COPY COMPLETE!")
        print("="*60)


def main():
    """Main entry point."""
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description='Copy source code and issues from one GitHub repository to another.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --source owner/source-repo --dest owner/dest-repo
  %(prog)s -s owner/source-repo -d owner/dest-repo --token ghp_xxxx
  
Environment Variables:
  GITHUB_TOKEN    GitHub personal access token for API access

Note:
  If no token is provided, the script will attempt to use the GitHub CLI (gh) if available.
        """
    )
    
    parser.add_argument(
        '-s', '--source',
        required=True,
        metavar='OWNER/REPO',
        help='Source repository in format "owner/repo"'
    )
    
    parser.add_argument(
        '-d', '--dest',
        required=True,
        metavar='OWNER/REPO',
        help='Destination repository in format "owner/repo"'
    )
    
    parser.add_argument(
        '-t', '--token',
        metavar='TOKEN',
        help='GitHub personal access token (or set GITHUB_TOKEN env var, or use GitHub CLI)'
    )
    
    parser.add_argument(
        '-f', '--force',
        action='store_true',
        help='Force copy even if destination repository is not empty'
    )
    
    parser.add_argument(
        '--copy-closed-issues',
        action='store_true',
        help='Copy closed issues in addition to open issues (default: only open issues)'
    )
    
    args = parser.parse_args()
    
    # Validate repository format
    for repo_name, repo_value in [('source', args.source), ('dest', args.dest)]:
        if '/' not in repo_value or len(repo_value.split('/')) != 2:
            parser.error(f"Invalid {repo_name} repository format: '{repo_value}'. Expected format: 'owner/repo'")
    
    # Get GitHub token from argument, environment, or GitHub CLI
    github_token = args.token or os.environ.get('GITHUB_TOKEN')
    
    if not github_token:
        # Try to get token from GitHub CLI
        github_token = get_github_token_from_cli()
        if github_token:
            print("Using GitHub token from GitHub CLI (gh auth token)")
    
    if not github_token:
        parser.error("GitHub token is required. Provide via --token, set GITHUB_TOKEN environment variable, or login with GitHub CLI (gh auth login).")
    
    # Create copier instance
    copier = RepoContentCopier(
        source_repo=args.source,
        dest_repo=args.dest,
        github_token=github_token
    )
    
    # Perform the copy
    copier.copy_all(force=args.force, include_closed_issues=args.copy_closed_issues)


if __name__ == "__main__":
    main()
