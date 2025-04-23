###############################################################################
# IMPORTANT: This header comment is designed for GenAI code review and maintenance
# Any GenAI tool working with this file MUST preserve and update this header
###############################################################################
# [GenAI coding tool directive]
# - Maintain this header with all modifications
# - Update History section with each change
# - Keep only the 4 most recent records in the history section. Sort from newer to older.
# - Preserve Intent, Design, and Constraints sections
# - Use this header as context for code reviews and modifications
# - Ensure all changes align with the design principles
# - Respect system prompt directives at all times
###############################################################################
# [Source file intent]
# Implements the ProjectConfigManager class, responsible for managing the
# context of the currently active project and loading its specific configuration
# by interacting with the main ConfigurationManager.
###############################################################################
# [Source file design principles]
# - Provides a clear interface for setting and getting the active project context.
# - Delegates the actual loading and merging of project-specific configuration
#   to the ConfigurationManager singleton.
# - Ensures that project root paths are valid directories.
# - Allows clearing the project context to revert to global/user configuration.
# - Design Decision: Separate Project Config Manager (2025-04-14)
#   * Rationale: Isolates project context management from the core configuration loading logic, making the system cleaner.
#   * Alternatives considered: Integrating project loading directly into ConfigurationManager (rejected for mixing concerns).
###############################################################################
# [Source file constraints]
# - Requires an instance of ConfigurationManager.
# - Assumes ConfigurationManager has a `load_project_config` method.
# - Project root path must be a valid directory.
###############################################################################
# [Dependencies]
# codebase:- doc/CONFIGURATION.md
# codebase:- doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T09:37:25Z : Initial creation of ProjectConfigManager class by CodeAssistant
# * Implemented methods for setting, getting, and clearing project context.
###############################################################################

import os
import logging
from pathlib import Path
from typing import Optional

# Assuming config_manager.py is accessible
try:
    from .config_manager import ConfigurationManager
except ImportError:
    # Allow running standalone for testing if needed
    from config_manager import ConfigurationManager

logger = logging.getLogger(__name__)

class ProjectConfigManager:
    """
    Manages the context for project-specific configuration loading.
    Interacts with the singleton ConfigurationManager to apply project settings.
    """

    def __init__(self, config_manager: ConfigurationManager = None):
        """
        Initializes the ProjectConfigManager.

        Args:
            config_manager: An instance of ConfigurationManager. If None,
                            the singleton instance will be retrieved.
        """
        # Use the provided config_manager or get the singleton instance
        self.config_manager = config_manager or ConfigurationManager()
        if not isinstance(self.config_manager, ConfigurationManager):
             raise TypeError("config_manager must be an instance of ConfigurationManager")

        self.current_project_root: Optional[str] = None
        logger.debug("ProjectConfigManager initialized.")

    def set_project(self, project_root: str) -> bool:
        """
        Sets the current project context and triggers loading of its specific configuration
        via the main ConfigurationManager.

        Args:
            project_root: The absolute or relative path to the root directory of the project.

        Returns:
            True if the project was set and its configuration loaded successfully, False otherwise.
        """
        logger.info(f"Attempting to set project context to: {project_root}")

        try:
            project_path = Path(project_root).resolve() # Resolve to absolute path
        except Exception as e:
            logger.error(f"Invalid project root path provided: {project_root}. Error: {e}")
            return False

        if not project_path.is_dir():
            logger.error(f"Project root path is not a valid directory: {project_path}")
            return False

        normalized_project_root = str(project_path)

        if self.current_project_root == normalized_project_root:
            logger.info(f"Project context already set to: {normalized_project_root}")
            return True # No change needed, already set

        try:
            # Delegate loading and hierarchy application to the main ConfigurationManager
            # This ensures project config overrides user/system config correctly.
            self.config_manager.load_project_config(normalized_project_root, apply_hierarchy=True)

            # Update the current project context *after* successful loading
            self.current_project_root = normalized_project_root
            logger.info(f"Successfully set project context and loaded config for: {normalized_project_root}")
            return True
        except Exception as e:
            # Catch potential errors during config loading/applying
            logger.error(f"Failed to set project context or load configuration for {normalized_project_root}: {e}", exc_info=True)
            # Should we clear the project context on failure? Maybe not, keep previous state.
            # self.clear_project() # Or maybe revert to previous state if possible?
            return False

    def get_project_root(self) -> Optional[str]:
        """
        Gets the root path of the currently active project.

        Returns:
            The absolute project root path as a string, or None if no project is set.
        """
        return self.current_project_root

    def clear_project(self):
        """
        Clears the current project context. This triggers the ConfigurationManager
        to re-initialize its state based on non-project sources (system, user, env, cli).
        """
        if self.current_project_root is None:
            logger.debug("No project context set, nothing to clear.")
            return

        current_cleared_root = self.current_project_root
        logger.info(f"Clearing project context from: {current_cleared_root}")
        self.current_project_root = None

        try:
            # Re-initialize the main config manager without project context.
            # This effectively removes the project layer from the hierarchy.
            # We need to pass the original CLI args again if they were used initially.
            # Accessing internal _cli_args is not ideal, but necessary here.
            # A better design might involve storing initial args more formally.
            cli_args_list = [f"--{k}={v}" for k, v in self.config_manager._cli_args.items()]
            self.config_manager.initialize(args=cli_args_list, project_root=None)
            logger.info("Project configuration cleared. Configuration re-initialized without project context.")
        except Exception as e:
            logger.error(f"Error occurred while re-initializing configuration after clearing project '{current_cleared_root}': {e}", exc_info=True)
            # The project context is cleared, but config might be in an unexpected state.

# Example Usage:
# config_manager = ConfigurationManager()
# config_manager.initialize() # Initial load without project
#
# project_manager = ProjectConfigManager(config_manager)
# if project_manager.set_project("/path/to/my/project"):
#     db_type = config_manager.get("database.type") # Should now reflect project config if overridden
#     print(f"DB type for project: {db_type}")
#
# project_manager.clear_project()
# db_type_after_clear = config_manager.get("database.type") # Should revert to user/system/default
# print(f"DB type after clearing project: {db_type_after_clear}")
