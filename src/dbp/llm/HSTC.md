# Hierarchical Semantic Tree Context - LLM Module

This directory contains components for managing interactions with Large Language Models (LLMs), specifically AWS Bedrock models. It provides client implementations, model management, and prompt handling for the DBP system.

## Child Directory Summaries
*No child directories with HSTC.md files.*

## Local File Headers

### Filename 'bedrock_base.py':
**Intent:** Defines the base class for Bedrock model clients, providing common functionality and interfaces that all model-specific implementations must follow.

**Design principles:**
- Abstract base class with common functionality for all Bedrock clients
- Standardized error handling across model implementations
- Consistent initialization and configuration pattern
- Centralized logging configuration

**Constraints:**
- Must work with AWS Bedrock API consistently
- Must handle transient failures gracefully
- Requires proper AWS credentials configuration

**Change History:**
- 2025-04-16T11:30:00Z : Initial creation of BedrockModelClientBase

### Filename 'bedrock_client_common.py':
**Intent:** Implements common utility functions and shared code used by all Bedrock model clients to avoid duplication across client implementations.

**Design principles:**
- Centralized utilities for authentication, retry logic, and error handling
- Common request formatting and response parsing
- Reusable client configuration patterns
- Consistent error taxonomy

**Constraints:**
- Must maintain compatibility with all supported Bedrock models
- Should abstract away low-level API differences between models

**Change History:**
- 2025-04-16T11:45:00Z : Initial creation with common Bedrock client utilities

### Filename 'bedrock_manager.py':
**Intent:** Implements a central manager for all Bedrock model clients. This manager serves as the main entry point for all Bedrock LLM operations, providing a unified interface for accessing various model clients and handling their lifecycle.

**Design principles:**
- Centralize Bedrock client management across the application
- Lazily initialize model clients only when needed
- Cache clients for reuse to optimize resource usage
- Provide a simple interface for retrieving clients by name
- Handle configuration loading and default values
- Support clean shutdown of all active clients

**Constraints:**
- Must support multiple model types with different parameter requirements
- Must not hardcode AWS credentials or region information
- Must handle model unavailability gracefully
- Must be thread-safe for concurrent access from multiple components

**Change History:**
- 2025-04-16T13:00:00Z : Initial creation of Bedrock client manager
  * Implemented client registry and lazy initialization
  * Added support for configuration-based client creation
  * Created interface for retrieving model clients by name

### Filename 'claude3_7_client.py':
**Intent:** Implements a specific client for the Claude 3.7 Sonnet model, handling all model-specific request formatting, response parsing, and parameter validation.

**Design principles:**
- Extends BedrockModelClientBase with Claude 3.7 specific implementations
- Optimized parameter defaults for Claude 3.7 model
- Specialized Claude 3.7 response parsing
- Efficient context handling for this specific model

**Constraints:**
- Must follow Claude 3.7 API specifications
- Must handle Claude 3.7 specific response formats
- Should optimize for Claude 3.7's strengths and limitations

**Change History:**
- 2025-04-16T14:15:00Z : Initial implementation of Claude 3.7 Sonnet client

### Filename 'nova_lite_client.py':
**Intent:** Implements a specific client for the Amazon Nova Lite model, handling all model-specific request formatting, response parsing, and parameter validation.

**Design principles:**
- Extends BedrockModelClientBase with Nova Lite specific implementations
- Optimized parameter defaults for Nova Lite model
- Specialized Nova Lite response parsing
- Efficient context handling for this specific model

**Constraints:**
- Must follow Nova Lite API specifications
- Must handle Nova Lite specific response formats
- Should optimize for Nova Lite's strengths and limitations

**Change History:**
- 2025-04-16T14:00:00Z : Initial implementation of Nova Lite client

### Filename 'prompt_manager.py':
**Intent:** Provides utilities for loading, processing, and managing prompts used with LLM models. This includes template substitution, parameter validation, and prompt optimization.

**Design principles:**
- Separation of prompt templates from application logic
- Support for template variables and substitution
- Utilities for prompt optimization and truncation
- Consistent prompt formatting across models

**Constraints:**
- Must handle different model-specific prompt formats
- Should provide efficient template substitution
- Must validate prompts against model constraints

**Change History:**
- 2025-04-16T12:30:00Z : Initial implementation of prompt management utilities
