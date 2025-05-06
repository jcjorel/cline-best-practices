#!/usr/bin/env python3
"""
Simple test script for the model availability table functionality.

This script demonstrates the use of get_model_availability_table 
and format_availability_table methods in BedrockModelCapabilities.

Usage:
    python test_availability_table.py [model_id]
    
    model_id: Optional model ID to filter the table
"""

import os
import sys
import argparse

# Add parent directories to Python path for direct imports
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
sys.path.insert(0, parent_dir)

# Import the capabilities class
from dbp.llm.bedrock.discovery.models_capabilities import BedrockModelCapabilities

def main():
    """Display model availability table."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Display model availability table")
    parser.add_argument("model_id", nargs='?', default=None, 
                        help="Optional model ID to filter the table")
    args = parser.parse_args()
    
    # Get instance of BedrockModelCapabilities
    model_capabilities = BedrockModelCapabilities.get_instance()
    
    # Generate the availability table
    print(f"Generating model availability table{' for ' + args.model_id if args.model_id else ''}...")
    table_data = model_capabilities.get_model_availability_table(model_id=args.model_id)
    
    # Format and print the table
    formatted_table = model_capabilities.format_availability_table(table_data)
    print(formatted_table)
    
if __name__ == "__main__":
    main()
