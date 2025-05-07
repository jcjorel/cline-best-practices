#!/usr/bin/env python3
"""
Direct AWS Bedrock API testing script for models and inference profiles.

This script directly uses boto3 to:
1. Fetch all models in us-east-1
2. Fetch all inference profiles in us-east-1
3. Filter for Nova and Claude models/profiles
4. Map inference profiles to models based on modelArns
5. Output the merged data structure

This helps understand how AWS Bedrock APIs work without any custom discovery classes.
"""

import boto3
import json
import logging
from datetime import datetime
import os
import sys

# Add parent directories to Python path for direct imports when running directly
if __name__ == "__main__":
    parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
    sys.path.insert(0, parent_dir)
    
    # Import client factory for AWS credentials
    from dbp.api_providers.aws.client_factory import AWSClientFactory

# Configure logging
