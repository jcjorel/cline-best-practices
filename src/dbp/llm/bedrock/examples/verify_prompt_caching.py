#!/usr/bin/env python3
"""
Verification script for prompt caching implementation.

This script verifies that all requirements for prompt caching have been met:
1. Ability to check if a model supports prompt caching
2. API to enable prompt caching for a conversation
3. API to mark cache points in a conversation
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional

from dbp.llm.bedrock.enhanced_base import ModelCapability, EnhancedBedrockBase
from dbp.llm.bedrock.models.claude3 import ClaudeClient
from dbp.llm.bedrock.discovery.models import BedrockModelDiscovery

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("prompt_caching_verification")

class VerificationResult:
    """Container for verification results."""
    
    def __init__(self):
        self.requirements = {
            "model_support_detection": False,
            "enable_caching_api": False,
            "mark_cache_point_api": False
        }
        self.details = {}
        
    def set_result(self, requirement: str, passed: bool, details: str):
        """Set result for a requirement."""
        self.requirements[requirement] = passed
        self.details[requirement] = details
    
    def all_passed(self) -> bool:
        """Check if all requirements passed."""
        return all(self.requirements.values())
    
    def summary(self) -> str:
        """Get summary of verification results."""
        result = "Verification Results:\n"
        result += "=" * 50 + "\n\n"
        
        for req, passed in self.requirements.items():
            status = "✅ PASSED" if passed else "❌ FAILED"
            result += f"{status}: {req}\n"
            result += f"   {self.details.get(req, 'No details')}\n\n"
        
        result += f"Overall Status: {'✅ PASSED' if self.all_passed() else '❌ FAILED'}\n"
        return result

async def verify_model_support_detection() -> Dict[str, Any]:
    """Verify ability to check if a model supports prompt caching."""
    result = {
        "passed": False,
        "details": ""
    }
    
    try:
        # Get model discovery instance
        discovery = BedrockModelDiscovery.get_instance()
        
        # Test with a model that should support caching
        support_claude = discovery.supports_prompt_caching("anthropic.claude-3-5-haiku-20241022-v1:0")
        
        # Test with a model that shouldn't support caching
        support_other = discovery.supports_prompt_caching("amazon.titan-text-express-v1")
        
        # Check if function exists and returns expected results
        if support_claude is True and support_other is False:
            result["passed"] = True
            result["details"] = "Model support detection correctly identifies supported and unsupported models"
        else:
            result["details"] = f"Unexpected results: Claude support: {support_claude}, Other support: {support_other}"
    except Exception as e:
        result["details"] = f"Error verifying model support detection: {str(e)}"
    
    return result

async def verify_enable_caching_api() -> Dict[str, Any]:
    """Verify API to enable prompt caching for a conversation."""
    result = {
        "passed": False,
        "details": ""
    }
    
    try:
        # Create a client with a supported model
        client = ClaudeClient("anthropic.claude-3-5-haiku-20241022-v1:0", logger=logger)
        
        # Mock initialization
        client._initialized = True
        
        # Test enabling caching
        with patch.object(client, 'has_capability', return_value=True):
            enabled = client.enable_prompt_caching(True)
            status = client.is_prompt_caching_enabled()
            
            if enabled is True and status is True:
                # Test disabling caching
                disabled = client.enable_prompt_caching(False)
                status = client.is_prompt_caching_enabled()
                
                if disabled is False and status is False:
                    result["passed"] = True
                    result["details"] = "Enable/disable prompt caching API works correctly"
                else:
                    result["details"] = f"Failed to disable caching: disabled={disabled}, status={status}"
            else:
                result["details"] = f"Failed to enable caching: enabled={enabled}, status={status}"
    except Exception as e:
        result["details"] = f"Error verifying enable caching API: {str(e)}"
    
    return result

async def verify_mark_cache_point_api() -> Dict[str, Any]:
    """Verify API to mark cache points in a conversation."""
    result = {
        "passed": False,
        "details": ""
    }
    
    try:
        # Create a client
        client = EnhancedBedrockBase("test-model", logger=logger)
        client._initialized = True
        
        # Test messages
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Tell me about AWS."}
        ]
        
        # Test with caching disabled
        with patch.object(client, 'is_prompt_caching_enabled', return_value=False):
            disabled_result = client.mark_cache_point(messages)
            
            if (disabled_result["status"] == "ignored" 
                    and disabled_result["cache_active"] is False 
                    and disabled_result["messages"] == messages):
                
                # Test with caching enabled
                with patch.object(client, 'is_prompt_caching_enabled', return_value=True):
                    enabled_result = client.mark_cache_point(messages)
                    
                    if (enabled_result["status"] == "marked" 
                            and enabled_result["cache_active"] is True
                            and "metadata" in enabled_result["messages"][-1]
                            and "cache_point" in enabled_result["messages"][-1]["metadata"]):
                        
                        result["passed"] = True
                        result["details"] = "Cache point marking API works correctly"
                    else:
                        result["details"] = f"Failed with caching enabled: {enabled_result}"
            else:
                result["details"] = f"Failed with caching disabled: {disabled_result}"
    except Exception as e:
        result["details"] = f"Error verifying mark cache point API: {str(e)}"
    
    return result

async def run_verification() -> VerificationResult:
    """Run all verification checks."""
    # Import unittest.mock only when needed for verification
    global patch
    from unittest.mock import patch
    
    verification = VerificationResult()
    
    # Check model support detection
    model_support = await verify_model_support_detection()
    verification.set_result(
        "model_support_detection", 
        model_support["passed"], 
        model_support["details"]
    )
    
    # Check enable caching API
    enable_caching = await verify_enable_caching_api()
    verification.set_result(
        "enable_caching_api", 
        enable_caching["passed"], 
        enable_caching["details"]
    )
    
    # Check mark cache point API
    mark_cache_point = await verify_mark_cache_point_api()
    verification.set_result(
        "mark_cache_point_api", 
        mark_cache_point["passed"], 
        mark_cache_point["details"]
    )
    
    return verification

async def main():
    """Main entry point."""
    logger.info("Starting prompt caching verification")
    
    try:
        result = await run_verification()
        print(result.summary())
        
        if result.all_passed():
            logger.info("All verification checks passed!")
        else:
            logger.error("Some verification checks failed. See summary for details.")
    except Exception as e:
        logger.error(f"Error during verification: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
