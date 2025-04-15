# src/dbp/core/__init__.py

"""
Core package for the Documentation-Based Programming system.

Contains the fundamental building blocks for the application's structure
and lifecycle management, including the component initialization framework.

Key components:
- Component: Protocol defining the component interface.
- InitializationContext: Dataclass for passing context during initialization.
- ComponentRegistry: Manages registration and retrieval of components.
- DependencyResolver: Determines component initialization order.
- InitializationOrchestrator: Manages the component lifecycle (init/shutdown).
- LifecycleManager: High-level application entry point managing the overall lifecycle.
"""

from .component import Component, InitializationContext
from .registry import ComponentRegistry
from .resolver import DependencyResolver, CircularDependencyError
from .orchestrator import InitializationOrchestrator
from .lifecycle import LifecycleManager

__all__ = [
    "Component",
    "InitializationContext",
    "ComponentRegistry",
    "DependencyResolver",
    "CircularDependencyError",
    "InitializationOrchestrator",
    "LifecycleManager",
]
