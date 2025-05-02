# Hierarchical Semantic Tree Context: langchain

## Directory Purpose
This directory implements integration adapters and utilities for connecting the DBP application's LLM subsystem with the LangChain ecosystem. It provides seamless compatibility between DBP's streaming-first LLM clients and LangChain's interfaces, enabling the use of custom LLM implementations with LangChain's chains, agents, and other components. The architecture ensures consistent callback handling, proper error propagation, and efficient streaming support while maintaining the flexibility to adapt to evolving LangChain interfaces.

## Local Files

### `__init__.py`
```yaml
source_file_intent: |
  Initialize the LangChain integration module, which provides adapters and utilities
  for integrating custom LLM clients with the LangChain ecosystem. This module
  enables seamless use of our LLM implementations with LangChain's components.
  
source_file_design_principles: |
  - Clean organization of LangChain integration components
  - Convenient imports for essential functionality
  - Minimal dependencies for core functionality
  - Support for both LangChain and LangGraph ecosystems
  
source_file_constraints: |
  - Must maintain compatibility with LangChain's interfaces
  - Must not create circular dependencies
  - Must export only necessary components
  - Must be self-contained for core functionality
  
dependencies:
  - kind: codebase
    dependency: src/dbp/llm/common/base.py
  - kind: codebase
    dependency: src/dbp/llm/common/exceptions.py
  - kind: system
    dependency: langchain_core
  
change_history:
  - timestamp: "2025-05-02T11:25:00Z"
    summary: "Initial creation for LangChain/LangGraph integration"
    details: "Created LangChain integration module and added exports for adapters and factories"
```

### `adapters.py`
```yaml
source_file_intent: |
  Provides adapters that allow our custom LLM clients to be used with LangChain's
  interfaces. This enables seamless integration with LangChain's ecosystem of
  chains, agents, and tools while maintaining our streaming-first approach.
  
source_file_design_principles: |
  - Clean adaptation between our API and LangChain's interface
  - Streaming-first approach with callback integration
  - Proper error handling and fallback mechanisms
  - Minimal overhead for performance
  - Comprehensive docstrings for public methods
  
source_file_constraints: |
  - Must implement LangChain's BaseLLM interface correctly
  - Must handle all callback mechanisms as per LangChain specs
  - Must maintain compatibility with streaming responses
  - Must properly convert between response formats
  
dependencies:
  - kind: codebase
    dependency: src/dbp/llm/common/base.py
  - kind: codebase
    dependency: src/dbp/llm/common/exceptions.py
  - kind: system
    dependency: asyncio
  - kind: system
    dependency: typing
  - kind: system
    dependency: langchain_core
  
change_history:
  - timestamp: "2025-05-02T11:25:00Z"
    summary: "Initial creation for LangChain/LangGraph integration"
    details: "Implemented LangChainLLMAdapter for integration with LangChain, added streaming support with callbacks, added prompt handling and response conversion"
```

### `chat_adapters.py`
```yaml
source_file_intent: |
  Provides adapters that allow our custom LLM clients to be used with LangChain's
  chat model interfaces. This enables integration with chat-oriented components
  in LangChain while maintaining our streaming-first approach.
  
source_file_design_principles: |
  - Chat-specific adapter implementation
  - Support for LangChain chat message format
  - Streaming support for chat interactions
  - Proper handling of chat history and context
  
source_file_constraints: |
  - Must implement LangChain's BaseChatModel interface correctly
  - Must handle all chat-specific callback mechanisms
  - Must properly convert between message formats
  - Must maintain compatibility with streaming responses
  
dependencies:
  - kind: codebase
    dependency: src/dbp/llm/common/base.py
  - kind: codebase
    dependency: src/dbp/llm/common/exceptions.py
  - kind: system
    dependency: asyncio
  - kind: system
    dependency: typing
  - kind: system
    dependency: langchain_core
  
change_history:
  - timestamp: "2025-05-02T11:25:00Z"
    summary: "Initial creation for LangChain/LangGraph integration"
    details: "Implemented LangChainChatAdapter for integration with LangChain, added support for chat message formats, implemented streaming for chat interactions"
```

### `factories.py`
```yaml
source_file_intent: |
  Provides factory classes and functions for creating LangChain components 
  from our custom LLM clients. This enables easy configuration and instantiation
  of LangChain components that use our LLM implementations.
  
source_file_design_principles: |
  - Simplify creation of LangChain components
  - Maintain consistent configuration patterns
  - Support for both standard and custom LangChain components
  - Handle complex component configuration
  
source_file_constraints: |
  - Must correctly configure LangChain components
  - Must be compatible with LangChain's factory patterns
  - Must support different client configurations
  - Must handle dependency injection properly
  
dependencies:
  - kind: codebase
    dependency: src/dbp/llm/common/base.py
  - kind: codebase
    dependency: src/dbp/llm/langchain/adapters.py
  - kind: codebase
    dependency: src/dbp/llm/langchain/chat_adapters.py
  - kind: system
    dependency: langchain_core
  - kind: system
    dependency: langchain
  
change_history:
  - timestamp: "2025-05-02T11:25:00Z"
    summary: "Initial creation for LangChain/LangGraph integration"
    details: "Implemented LangChainFactory class for creating LangChain components, added support for standard LangChain components, implemented configuration utilities"
```

### `utils.py`
```yaml
source_file_intent: |
  Provides utility functions for LangChain integration, including tools conversion,
  callback management, and other helper functions to simplify working with LangChain.
  
source_file_design_principles: |
  - Reusable utility functions for common operations
  - Standardized conversion between DBP and LangChain formats
  - Support for LangChain's observability features
  - Helper functions to simplify integration
  
source_file_constraints: |
  - Must be compatible with LangChain's interfaces
  - Must handle format conversions correctly
  - Must support both standard and custom LangChain components
  - Must be maintainable as LangChain evolves
  
dependencies:
  - kind: codebase
    dependency: src/dbp/llm/common/tool_registry.py
  - kind: system
    dependency: langchain_core
  - kind: system
    dependency: langchain
  
change_history:
  - timestamp: "2025-05-02T11:25:00Z"
    summary: "Initial creation for LangChain/LangGraph integration"
    details: "Implemented utility functions for LangChain integration, added tool conversion, added tracing configuration utilities"
```

End of HSTC.md file
