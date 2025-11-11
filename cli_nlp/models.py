"""Pydantic models for structured LLM responses."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SafetyLevel(str, Enum):
    """Safety level of a command."""
    SAFE = "safe"  # Read-only operations
    MODIFYING = "modifying"  # Will alter system state (write files, change config, etc.)


class CommandResponse(BaseModel):
    """Structured response from LLM containing command and safety information."""
    
    command: str = Field(
        description="The shell command to execute. Only the command itself, no explanations or markdown."
    )
    
    is_safe: bool = Field(
        description="True if the command only reads/displays information. False if it will modify the system (write files, change configuration, delete data, etc.)."
    )
    
    safety_level: SafetyLevel = Field(
        description="Safety level of the command: 'safe' for read-only operations, 'modifying' for operations that alter system state."
    )
    
    explanation: Optional[str] = Field(
        default=None,
        description="Brief explanation of what the command does (optional, for user understanding)."
    )

