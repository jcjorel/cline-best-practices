#!/usr/bin/env python3
"""
Test script for component initialization with the new dependency injection mechanism.
This script initializes the system and reports any initialization issues.
"""

import logging
import sys
import os
from typing import Dict, Any

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import required modules
from src.dbp.core.registry import ComponentRegistry
from src.dbp.core.system import ComponentSystem

def setup_logging() -> None:
    """Set up basic logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

def test_initialization() -> Dict[str, Any]:
    """
    Test component initialization with the new dependency injection mechanism.
    
    Returns:
        Dict containing test results
    """
    logger = logging.getLogger("test_initialization")
    
    # Test results
    results = {
        "success": False,
        "components_registered": 0,
        "components_initialized": 0,
        "dependency_errors": [],
        "initialization_errors": [],
    }
    
    try:
        logger.info("Creating component registry...")
        registry = ComponentRegistry()
        
        # Create a mock config for testing
        mock_config = {"component_enabled": {}}
        
        # Create system
        logger.info("Creating component system...")
        system = ComponentSystem(mock_config, logger)
        
        # Register components with simple dependencies for testing
        logger.info("Registering test components...")
        
        # FileAccessComponent (no dependencies)
        from src.dbp.core.file_access_component import FileAccessComponent
        registry.register_component(FileAccessComponent, dependencies=[], enabled=True)
        results["components_registered"] += 1
        
        # ConfigManagerComponent (no dependencies)
        from src.dbp.config.component import ConfigManagerComponent
        from src.dbp.config.config_manager import ConfigurationManager
        config_manager = ConfigurationManager()
        config_manager.initialize()
        
        def config_manager_factory():
            return ConfigManagerComponent(config_manager)
        
        registry.register_component_factory(
            name="config_manager",
            factory=config_manager_factory,
            dependencies=[],
            enabled=True
        )
        results["components_registered"] += 1
        
        # Register with system
        logger.info("Registering components with system...")
        registry.register_with_system(system)
        
        # Validate dependencies
        logger.info("Validating component dependencies...")
        missing = system.validate_dependencies()
        if missing:
            results["dependency_errors"] = missing
            logger.error(f"Dependency validation failed with errors: {missing}")
        else:
            logger.info("All dependencies validated successfully")
            
            # Initialize components
            logger.info("Initializing components...")
            success = system.initialize_all()
            
            if success:
                results["success"] = True
                results["components_initialized"] = len(system._initialized)
                logger.info(f"Successfully initialized {results['components_initialized']} components")
            else:
                logger.error("Initialization failed")
                
        # Shutdown
        logger.info("Shutting down components...")
        system.shutdown_all()
                
    except Exception as e:
        logger.exception(f"Test failed with exception: {e}")
        results["initialization_errors"].append(str(e))
        
    return results

def main():
    """Main function."""
    setup_logging()
    logger = logging.getLogger("main")
    
    logger.info("Testing component initialization with dependency injection...")
    results = test_initialization()
    
    # Report results
    if results["success"]:
        logger.info("✅ Test passed! Component initialization with dependency injection works correctly.")
        logger.info(f"Registered components: {results['components_registered']}")
        logger.info(f"Initialized components: {results['components_initialized']}")
    else:
        logger.error("❌ Test failed! Component initialization with dependency injection failed.")
        if results["dependency_errors"]:
            logger.error(f"Dependency errors: {results['dependency_errors']}")
        if results["initialization_errors"]:
            logger.error(f"Initialization errors: {results['initialization_errors']}")
            
    return 0 if results["success"] else 1

if __name__ == "__main__":
    sys.exit(main())
