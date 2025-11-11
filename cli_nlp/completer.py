"""Tab completion for interactive query input using prompt_toolkit."""

import os
import subprocess
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from prompt_toolkit.completion import Completer, Completion, PathCompleter
from prompt_toolkit.document import Document


class QueryCompleter(Completer):
    """Completer for natural language queries with bash-style path completion."""
    
    def __init__(self):
        self.path_completer = PathCompleter(expanduser=True, only_directories=False)
        self.common_commands = [
            "list", "show", "find", "search", "display", "count",
            "create", "delete", "remove", "move", "copy", "rename",
            "grep", "cat", "less", "head", "tail", "sort", "uniq",
            "ls", "cd", "pwd", "mkdir", "rm", "cp", "mv", "touch",
            "git", "docker", "kubectl", "npm", "pip", "poetry",
        ]
        self._command_cache = None
    
    def get_completions(
        self, document: Document, complete_event
    ) -> Iterable[Completion]:
        """Generate completions for the current input."""
        # Check if we're in a path context by looking at the text around cursor
        if self._is_in_path_context(document):
            # Complete paths using our custom path completion
            yield from self._complete_path_custom(document)
            return
        
        # Get word for command completion
        word_before_cursor = document.get_word_before_cursor(WORD=True)
        
        # Otherwise, suggest common command words and bash commands
        yield from self._complete_commands(word_before_cursor)
    
    def _extract_path_document(self, document: Document) -> tuple[Document, int]:
        """Extract the path portion from the document for path completion.
        
        Returns:
            Tuple of (path_document, offset) where offset is the position of path start in original document
        """
        import re
        
        text_before = document.text_before_cursor
        text_after = document.text_after_cursor
        
        # Find the path in the text
        # Look for patterns: /path, ~/path, ./path
        match = re.search(r'([/~]|\./)[^\s]*$', text_before)
        if match:
            # Extract the path portion
            path_start = match.start()
            path_text = text_before[path_start:] + text_after
            
            # Create a new document with just the path
            # The cursor position in the new document is at the end of path_text before text_after
            cursor_pos = len(text_before) - path_start
            path_doc = Document(path_text, cursor_pos)
            return path_doc, path_start
        
        # Also handle case where we're right after a path indicator
        if text_before.endswith('/') or text_before.endswith('~/') or text_before.endswith('./'):
            if text_before.endswith('./'):
                path_text = './' + text_after
                offset = len(text_before) - 2
            else:
                path_text = text_before[-1:] + text_after
                offset = len(text_before) - 1
            path_doc = Document(path_text, len(path_text) - len(text_after))
            return path_doc, offset
        
        return None, 0
    
    def _complete_path_custom(self, document: Document) -> Iterable[Completion]:
        """Custom path completion that handles paths in natural language queries."""
        import os
        from pathlib import Path
        
        text_before = document.text_before_cursor
        
        # Extract the path being completed
        path_match = None
        import re
        
        # Find path pattern
        match = re.search(r'([/~]|\./)[^\s]*$', text_before)
        if match:
            path_start = match.start()
            path_text = text_before[path_start:]
            
            # Determine the directory and file part
            if '/' in path_text:
                # Split into directory and filename
                last_slash = path_text.rfind('/')
                dir_part = path_text[:last_slash + 1]
                file_part = path_text[last_slash + 1:]
            else:
                dir_part = path_text
                file_part = ""
            
            # Resolve the directory
            try:
                if dir_part.startswith('~/'):
                    base_dir = Path.home() / dir_part[2:]
                elif dir_part.startswith('./'):
                    base_dir = Path(dir_part[2:])
                elif dir_part.startswith('/'):
                    base_dir = Path(dir_part)
                elif dir_part.startswith('~'):
                    base_dir = Path.home() / dir_part[1:]
                else:
                    base_dir = Path('.') / dir_part
                
                # Expand user if needed
                base_dir = base_dir.expanduser()
                
                if base_dir.exists() and base_dir.is_dir():
                    # List directory contents
                    try:
                        for item in os.listdir(base_dir):
                            if item.startswith(file_part):
                                item_path = base_dir / item
                                if item_path.is_dir():
                                    completion_text = item + '/'
                                else:
                                    completion_text = item
                                
                                # Calculate start position relative to cursor
                                start_pos = -len(file_part)
                                yield Completion(
                                    completion_text,
                                    start_position=start_pos,
                                    display_meta="directory" if item_path.is_dir() else "file"
                                )
                    except PermissionError:
                        pass
            except Exception:
                pass
    
    def _is_in_path_context(self, document: Document) -> bool:
        """Check if cursor is in a path completion context."""
        import re
        
        text_before = document.text_before_cursor
        
        # Simple and reliable: if we see a path indicator (/ or ~/ or ./) 
        # in the text before cursor and there's no space after it, we're in a path
        
        # Check for absolute paths: /something
        if '/' in text_before:
            # Find the last / in the text
            last_slash_idx = text_before.rfind('/')
            if last_slash_idx >= 0:
                # Check what's after the slash
                after_slash = text_before[last_slash_idx + 1:]
                # If there's no space after the slash, we're likely in a path
                if ' ' not in after_slash:
                    # Check if it's a valid path start (/, ~/, or ./)
                    before_slash = text_before[:last_slash_idx + 1]
                    # Check if it starts with /, ~/, or ./ or has a space before /
                    if (before_slash.endswith('/') or 
                        before_slash.endswith('~/') or 
                        before_slash.endswith('./') or
                        (last_slash_idx > 0 and text_before[last_slash_idx - 1] == ' ')):
                        return True
        
        # Check for home directory paths: ~/something
        if '~/' in text_before:
            tilde_idx = text_before.rfind('~/')
            if tilde_idx >= 0:
                after_tilde = text_before[tilde_idx + 2:]
                if ' ' not in after_tilde:
                    return True
        
        # Check for relative paths: ./something
        if './' in text_before:
            dot_idx = text_before.rfind('./')
            if dot_idx >= 0:
                after_dot = text_before[dot_idx + 2:]
                if ' ' not in after_dot:
                    return True
        
        # Also check if we're typing right after a path indicator
        if text_before.endswith('/') or text_before.endswith('~/') or text_before.endswith('./'):
            return True
        
        return False
    
    def _complete_commands(self, word: str) -> Iterable[Completion]:
        """Complete command names using bash completion."""
        word_lower = word.lower()
        
        # First, suggest common command words
        for cmd in self.common_commands:
            if cmd.startswith(word_lower):
                yield Completion(cmd, start_position=-len(word))
        
        # Then try bash's compgen for system commands
        # Cache commands for performance
        if self._command_cache is None:
            self._command_cache = self._get_system_commands()
        
        for cmd in self._command_cache:
            if cmd.startswith(word) and cmd not in self.common_commands:
                yield Completion(cmd, start_position=-len(word))
    
    def _get_system_commands(self) -> List[str]:
        """Get list of system commands using bash compgen."""
        commands = []
        try:
            result = subprocess.run(
                ["bash", "-c", "compgen -c"],
                capture_output=True,
                text=True,
                timeout=0.5
            )
            if result.returncode == 0:
                commands = sorted(set(result.stdout.strip().split("\n")))
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            pass
        return commands
