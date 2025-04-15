# src/dbp/config/__init__.py

"""
Configuration management package for the Documentation-Based Programming system.

This package includes:
- Configuration schema definition using Pydantic (`config_schema.py`).
- A singleton manager for loading and accessing configuration (`config_manager.py`).
- A helper for managing project-specific configuration contexts (`project_config.py`).
"""

# Make key classes easily importable from the package level
from .config_schema import AppConfig
from .config_manager import ConfigurationManager
from .project_config import ProjectConfigManager

__all__ = [
    "AppConfig",
    "ConfigurationManager",
    "ProjectConfigManager",
]
