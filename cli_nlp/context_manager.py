"""Context management for CLI-NLP to provide better command generation."""

import os
import subprocess
from pathlib import Path
from typing import Dict, Optional


class ContextManager:
    """Manages context information for command generation."""
    
    def __init__(self):
        self._context_cache: Dict[str, any] = {}
    
    def get_current_directory(self) -> str:
        """Get current working directory."""
        return os.getcwd()
    
    def get_git_context(self) -> Optional[Dict[str, str]]:
        """Get git repository context if in a git repo."""
        try:
            # Check if we're in a git repo
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
                timeout=1
            )
            if result.returncode != 0:
                return None
            
            context = {}
            
            # Get git status
            status_result = subprocess.run(
                ["git", "status", "--short"],
                capture_output=True,
                text=True,
                timeout=1
            )
            if status_result.returncode == 0:
                context["status"] = status_result.stdout.strip()
            
            # Get current branch
            branch_result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                timeout=1
            )
            if branch_result.returncode == 0:
                context["branch"] = branch_result.stdout.strip()
            
            # Get remote info
            remote_result = subprocess.run(
                ["git", "remote", "-v"],
                capture_output=True,
                text=True,
                timeout=1
            )
            if remote_result.returncode == 0:
                context["remotes"] = remote_result.stdout.strip()
            
            return context if context else None
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            return None
    
    def get_environment_context(self) -> Dict[str, str]:
        """Get relevant environment variables."""
        relevant_vars = [
            "VIRTUAL_ENV",
            "CONDA_DEFAULT_ENV",
            "PYTHON_VERSION",
            "PATH",
            "HOME",
            "USER",
            "SHELL",
        ]
        
        context = {}
        for var in relevant_vars:
            value = os.getenv(var)
            if value:
                # Truncate PATH if too long
                if var == "PATH" and len(value) > 200:
                    context[var] = value[:200] + "..."
                else:
                    context[var] = value
        
        return context
    
    def get_filesystem_context(self, max_depth: int = 2) -> Dict[str, any]:
        """Get filesystem context (directory structure)."""
        try:
            cwd = Path(self.get_current_directory())
            context = {
                "current_directory": str(cwd),
                "files": [],
                "directories": [],
            }
            
            # List top-level files and directories
            try:
                for item in cwd.iterdir():
                    if item.is_file():
                        context["files"].append(item.name)
                    elif item.is_dir():
                        context["directories"].append(item.name)
                
                # Limit to avoid too much context
                context["files"] = sorted(context["files"])[:20]
                context["directories"] = sorted(context["directories"])[:20]
            except PermissionError:
                pass
            
            return context
        except Exception:
            return {"current_directory": str(self.get_current_directory())}
    
    def get_shell_context(self) -> Dict[str, str]:
        """Get shell-related context."""
        shell = os.getenv("SHELL", "/bin/bash")
        shell_name = Path(shell).name
        
        return {
            "shell": shell,
            "shell_name": shell_name,
        }
    
    def build_context_string(self, include_git: bool = True) -> str:
        """Build a context string for inclusion in prompts."""
        context_parts = []
        
        # Current directory
        cwd = self.get_current_directory()
        context_parts.append(f"Current directory: {cwd}")
        
        # Git context
        if include_git:
            git_ctx = self.get_git_context()
            if git_ctx:
                git_info = []
                if "branch" in git_ctx:
                    git_info.append(f"branch: {git_ctx['branch']}")
                if "status" in git_ctx:
                    git_info.append(f"status: {git_ctx['status'][:100]}")
                if git_info:
                    context_parts.append(f"Git context: {', '.join(git_info)}")
        
        # Environment context
        env_ctx = self.get_environment_context()
        if "VIRTUAL_ENV" in env_ctx:
            context_parts.append(f"Virtual environment: {env_ctx['VIRTUAL_ENV']}")
        
        # Shell context
        shell_ctx = self.get_shell_context()
        context_parts.append(f"Shell: {shell_ctx['shell_name']}")
        
        return "\n".join(context_parts)
    
    def get_full_context(self) -> Dict[str, any]:
        """Get all available context information."""
        return {
            "current_directory": self.get_current_directory(),
            "git": self.get_git_context(),
            "environment": self.get_environment_context(),
            "filesystem": self.get_filesystem_context(),
            "shell": self.get_shell_context(),
        }

