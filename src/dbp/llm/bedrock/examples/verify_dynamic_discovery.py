#!/usr/bin/env python3
"""
Simple verification script for the dynamic model discovery system.

This script verifies the core functionality of the dynamic discovery system
without requiring external dependencies like LangChain or boto3.

Usage:
    python verify_dynamic_discovery.py
"""

import os
import sys
import importlib
import inspect
from pprint import pprint

# Add parent directories to Python path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
sys.path.insert(0, parent_dir)

# Import only the modules we need to test
try:
    from dbp.llm.bedrock.client_factory import (
        get_all_supported_model_ids,
        get_client_class_for_model,
        get_parameter_class_for_model,
        _ensure_caches_initialized
    )
    print("Successfully imported discovery functions.")
except Exception as e:
    print(f"Error importing discovery functions: {str(e)}")
    sys.exit(1)

def verify_client_factory():
    """Verify the client factory dynamic discovery system."""
    print("\n=== Verifying Dynamic Discovery System ===")
    
    # Initialize discovery
    try:
        _ensure_caches_initialized()
        print("✓ Discovery initialization successful")
    except Exception as e:
        print(f"✗ Discovery initialization failed: {str(e)}")
        return False
    
    # Get supported models
    try:
        supported_models = get_all_supported_model_ids()
        if supported_models:
            print(f"✓ Found {len(supported_models)} supported models")
            print("\nSupported Models:")
            for model_id in sorted(supported_models):
                print(f"  - {model_id}")
        else:
            print("✗ No supported models found")
            return False
    except Exception as e:
        print(f"✗ Error getting supported models: {str(e)}")
        return False
    
    # Check client and parameter classes
    if supported_models:
        example_model = sorted(supported_models)[0]
        print(f"\nTesting with example model: {example_model}")
        
        # Get client class
        try:
            client_class = get_client_class_for_model(example_model)
            print(f"✓ Found client class: {client_class.__name__}")
        except Exception as e:
            print(f"✗ Error getting client class: {str(e)}")
            return False
        
        # Get parameter class
        try:
            param_class = get_parameter_class_for_model(example_model)
            print(f"✓ Found parameter class: {param_class.__name__}")
        except Exception as e:
            print(f"✗ Error getting parameter class: {str(e)}")
            return False
        
        # Verify parameter classes in client class
        try:
            if hasattr(client_class, 'PARAMETER_CLASSES'):
                print(f"✓ Client class has PARAMETER_CLASSES with {len(client_class.PARAMETER_CLASSES)} entries")
                for param_class in client_class.PARAMETER_CLASSES:
                    print(f"  - {param_class.__name__}")
            else:
                print("✗ Client class does not have PARAMETER_CLASSES")
                return False
        except Exception as e:
            print(f"✗ Error inspecting PARAMETER_CLASSES: {str(e)}")
            return False
    
    print("\n=== Verification Complete ===")
    return True

if __name__ == "__main__":
    print("Starting dynamic discovery verification...")
    success = verify_client_factory()
    
    if success:
        print("\nSuccess: Dynamic discovery system is working correctly!")
        sys.exit(0)
    else:
        print("\nFailed: Issues found with dynamic discovery system.")
        sys.exit(1)
