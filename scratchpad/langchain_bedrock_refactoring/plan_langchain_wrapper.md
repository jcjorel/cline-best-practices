# Phase 1: Update `langchain_wrapper.py`

## Current Issues

The current implementation of `EnhancedChatBedrockConverse` in `langchain_wrapper.py` has a design issue where the `extract_text_from_chunk` method is trying to handle both Nova and Claude chunk formats in a single implementation. This violates the single responsibility principle and makes the code harder to maintain.

## Planned Changes

We'll modify the `EnhancedChatBedrockConverse` class to:

1. Keep the current `extract_text_from_chunk` method as a static method providing generic text extraction functionality.
2. Add a new `_extract_text_from_chunk` class method that will serve as a hook for model-specific implementations.
3. Update `astream`, `stream_text`, and `astream_text` methods to use the new `_extract_text_from_chunk` method.

### Code Changes

```python
class EnhancedChatBedrockConverse(ChatBedrockConverse):
    # Existing code...
    
    @staticmethod
    def extract_text_from_chunk(content):
        """
        [Method intent]
        Generic implementation that attempts to extract text from multiple formats.
        This will be kept for backwards compatibility and as a fallback.
        
        [Design principles]
        - Serves as a fallback implementation
        - Provides basic text extraction capabilities
        - Will be kept for backwards compatibility
        
        [Implementation details]
        - Simple extraction of text content from common formats
        - Handles the most generic cases only
        
        Args:
            content: Content from model in any format
            
        Returns:
            str: Extracted text or empty string
        """
        # Original implementation remains the same
        # This is kept for backward compatibility and as a public API
        
        # Handle empty content
        if not content:
            return ""
        
        # Handle LangChain ChatGenerationChunk objects
        if hasattr(content, "message") and hasattr(content.message, "content"):
            return content.message.content if content.message.content else ""
            
        # Handle LangChain AIMessageChunk objects
        if hasattr(content, "content") and isinstance(content.content, str):
            return content.content

        # Handle list content by processing each item
        if isinstance(content, list):
            result = ""
            for item in content:
                if item is not None:
                    result += EnhancedChatBedrockConverse.extract_text_from_chunk(item)
            return result
        
        # Handle dictionary content
        if isinstance(content, dict):
            # Check for text field (used by many models)
            if "text" in content:
                return content["text"]
            # Check for content field (used by some models)
            elif "content" in content:
                return content["content"]
            # For Amazon models using 'completion' field
            elif "completion" in content:
                return content["completion"]
            # For Anthropic models using 'delta' structure
            elif "delta" in content and isinstance(content["delta"], dict):
                if "text" in content["delta"]:
                    return content["delta"]["text"]
                elif "content" in content["delta"]:
                    return content["delta"]["content"]
            # For LangChain message format
            elif "message" in content and isinstance(content["message"], dict):
                if "content" in content["message"]:
                    return content["message"]["content"]
            return ""
        
        # Handle string content
        if isinstance(content, str):
            # If it looks like a JSON object, try to parse it
            if content.startswith("{") and content.endswith("}"):
                try:
                    # Convert Python dict notation to proper JSON if needed
                    json_content = content.replace("'", '"')
                    parsed_dict = orjson.loads(json_content)
                    
                    # Use recursive call to handle the parsed dictionary
                    return EnhancedChatBedrockConverse.extract_text_from_chunk(parsed_dict)
                except Exception:
                    # If parsing fails, return original content
                    return content
            return content
        
        # For any other type, convert to string and return
        return str(content) if content is not None else ""
    
    @classmethod
    def _extract_text_from_chunk(cls, content):
        """
        [Method intent]
        Model-specific text extraction hook. This method is meant to be overridden
        by model-specific subclasses to provide specialized text extraction.
        
        [Design principles]
        - Model-specific implementation hook
        - Clean separation of concerns
        - Clear contract for subclasses
        
        [Implementation details]
        - Default implementation uses the generic extract_text_from_chunk
        - Model-specific subclasses should override this method
        - Provides backward compatibility
        
        Args:
            content: Content from model in any format
            
        Returns:
            str: Clean text content without structure
        """
        # By default, use the generic implementation
        return cls.extract_text_from_chunk(content)
        
    # Update astream to use _extract_text_from_chunk
    async def astream(self, messages, **kwargs):
        """
        [Method intent]
        Override LangChain's astream method with built-in throttling retry logic.
        Now uses model-specific chunk extraction through _extract_text_from_chunk.
        
        [Design principles]
        - Same as original implementation
        - Uses model-specific text extraction
        
        [Implementation details]
        - Same as original implementation but calls _extract_text_from_chunk
        - Model-specific behavior without changing method signature
        
        Args, Returns, Raises: Same as original implementation
        """
        retry_count = 0
        
        while True:
            try:
                # Get parent's async generator - don't await it directly
                parent_generator = super()._astream(
                    messages=messages,
                    stop=kwargs.get("stop"),
                    run_manager=kwargs.get("run_manager"),
                    **kwargs
                )
                
                # Process each chunk as they come through the generator
                async for chunk in parent_generator:
                    # Extract text using model-specific implementation
                    text_content = self._extract_text_from_chunk(chunk)
                    yield AIMessageChunk(content=text_content)
                
                # Exit the retry loop once complete
                return
                
            except botocore.exceptions.ClientError as e:
                # Original error handling code remains unchanged
                error_code = e.response['Error']['Code']
                error_message = e.response['Error']['Message']
                
                if error_code == "ThrottlingException" and "Too many requests" in error_message:
                    retry_count += 1
                    
                    if retry_count <= self.max_retries:
                        # Calculate backoff with jitter
                        delay = min(self.max_delay, self.base_delay * (2 ** (retry_count - 1)))
                        jitter = random.uniform(0.8, 1.0)
                        delay_with_jitter = delay * jitter
                        
                        # Log retry attempt
                        warning_msg = f"Request throttled: {error_message}. Retry {retry_count}/{self.max_retries} in {delay_with_jitter:.2f}s"
                        self.logger.warning(warning_msg)
                        
                        # Wait before retry (async)
                        await asyncio.sleep(delay_with_jitter)
                        continue
                
                # For non-throttling or max-retries-exceeded cases, classify and raise
                if error_code == "ThrottlingException" and retry_count > self.max_retries:
                    raise InvocationError(
                        f"Request throttled (max retries exceeded): {error_message}", 
                        e
                    )
                
                # For other AWS errors, classify and raise
                raise self._classify_bedrock_error(e)
                
            except Exception as e:
                # Pass through our custom exceptions
                if isinstance(e, (ClientError, InvocationError, ModelNotAvailableError, StreamingError)):
                    raise e
                
                # Wrap other exceptions with StreamingError for async methods
                raise StreamingError(f"Bedrock streaming error: {str(e)}", e)
    
    # Update stream_text to use _extract_text_from_chunk
    def stream_text(self, messages: List[BaseMessage], **kwargs) -> Iterator[str]:
        """
        [Method intent]
        Stream clean text responses from the model without additional metadata or structure.
        
        [Design principles]
        - Provide a simpler interface for text-only responses
        - Filter out non-text elements from responses
        - Use model-specific text extraction
        
        [Implementation details]
        - Uses the enhanced stream method with retry logic
        - Uses _extract_text_from_chunk to get clean text
        - Returns a generator yielding only text strings
        
        Args:
            messages: List of BaseMessage objects representing conversation history
            **kwargs: Additional arguments to pass to the model
            
        Returns:
            Iterator[str]: A generator yielding clean text strings
            
        Raises:
            Same exceptions as the underlying stream method
        """
        for chunk in self.stream(messages, **kwargs):
            content = chunk.content
            clean_text = self._extract_text_from_chunk(content)
            if clean_text:
                yield clean_text
    
    # Update astream_text to use _extract_text_from_chunk
    async def astream_text(self, messages: List[BaseMessage], **kwargs) -> AsyncIterator[str]:
        """
        [Method intent]
        Asynchronously stream clean text responses from the model without additional metadata or structure.
        
        [Design principles]
        - Provide a simpler interface for text-only responses
        - Filter out non-text elements from responses
        - Use model-specific text extraction
        
        [Implementation details]
        - Uses the enhanced astream method with retry logic
        - Uses _extract_text_from_chunk to get clean text
        - Returns an async generator yielding only text strings
        
        Args:
            messages: List of BaseMessage objects representing conversation history
            **kwargs: Additional arguments to pass to the model
            
        Returns:
            AsyncIterator[str]: An async generator yielding clean text strings
            
        Raises:
            Same exceptions as the underlying astream method
        """
        async for chunk in self.astream(messages, **kwargs):
            content = chunk.content
            clean_text = self._extract_text_from_chunk(content)
            if clean_text:
                yield clean_text
```

## Benefits

1. **Cleaner Separation of Concerns**: Each model type will have its own specific implementation for chunk extraction.
2. **Extensibility**: New model types can be added by creating a new subclass with its own specialized extraction logic.
3. **Backward Compatibility**: The original `extract_text_from_chunk` static method remains for backward compatibility.
4. **Maintainability**: Changes to model-specific extraction logic can be isolated to relevant subclasses.

## Test Considerations

1. Test the default implementation of `_extract_text_from_chunk` to ensure it correctly uses the static method.
2. Test with both Claude and Nova format chunks to ensure the static method still works as expected.
