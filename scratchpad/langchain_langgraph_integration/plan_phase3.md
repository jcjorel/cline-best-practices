# Phase 3: AsyncIO Streaming Foundation

This phase implements the AsyncIO streaming foundation for the LangChain/LangGraph integration. It builds on the interfaces defined in Phase 2 to create concrete streaming components that handle chunk-based streaming responses and emulate streaming for non-streaming models.

## Objectives

1. Implement core streaming response classes
2. Create chunk aggregation utilities
3. Build stream emulation for non-streaming models
4. Implement stream transformation and composition utilities

## Streaming Response Implementation

Create the core streaming response class in `src/dbp/llm/common/streaming.py`:

```python
import asyncio
import logging
from typing import AsyncIterator, Dict, Any, List, Optional, Callable, TypeVar, Generic

from src.dbp.llm.common.exceptions import StreamingError

T = TypeVar('T')

class StreamingResponse(Generic[T]):
    """
    [Class intent]
    Represents a streaming response from an LLM with chunk-by-chunk delivery.
    This class handles the management of streaming data, including buffering,
    listener notifications, and stream completion.
    
    [Design principles]
    - Provides uniform interface for all streaming responses
    - Supports both real-time access and buffered access
    - Uses AsyncIO for non-blocking operation
    - Enables event-based notification for new chunks
    
    [Implementation details]
    - Uses asyncio queues for thread-safe chunk delivery
    - Implements the IStreamable interface
    - Manages listeners for real-time chunk notification
    - Buffers chunks for later access
    """
    
    def __init__(self):
        """
        [Method intent]
        Initialize a new streaming response.
        
        [Design principles]
        - Clean initialization with minimal dependencies
        - Preparation for both buffered and real-time access
        
        [Implementation details]
        - Sets up internal state for chunk management
        - Initializes empty buffers and listener lists
        - Creates event for tracking completion
        """
        self._chunks = []
        self._listeners = []
        self._complete = asyncio.Event()
        self._complete_listeners = []
        self._error = None
        self._logger = logging.getLogger(self.__class__.__name__)
    
    async def add_chunk(self, chunk: T) -> None:
        """
        [Method intent]
        Add a chunk to the response and notify listeners.
        
        [Design principles]
        - Thread-safe chunk addition
        - Immediate listener notification
        - No buffering delays for real-time access
        
        [Implementation details]
        - Appends chunk to internal buffer
        - Notifies all registered listeners
        - Uses async calls to avoid blocking
        
        Args:
            chunk: The chunk to add
            
        Raises:
            StreamingError: If the response has already completed or errored
        """
        if self.is_complete():
            raise StreamingError("Cannot add chunk to completed response")
        
        if self._error:
            raise StreamingError(f"Cannot add chunk to failed response: {self._error}")
        
        self._chunks.append(chunk)
        
        # Notify listeners
        for listener in self._listeners:
            try:
                await listener(chunk)
            except Exception as e:
                self._logger.error(f"Error in chunk listener: {e}")
    
    async def complete(self) -> None:
        """
        [Method intent]
        Mark the response as complete and notify completion listeners.
        
        [Design principles]
        - Clear indication of stream completion
        - Notification for completion-dependent operations
        
        [Implementation details]
        - Sets completion event
        - Notifies all completion listeners
        - Uses async calls to avoid blocking
        
        Raises:
            StreamingError: If the response has already completed or errored
        """
        if self.is_complete():
            raise StreamingError("Response already completed")
        
        if self._error:
            raise StreamingError(f"Cannot complete failed response: {self._error}")
        
        self._complete.set()
        
        # Notify completion listeners
        for listener in self._complete_listeners:
            try:
                await listener()
            except Exception as e:
                self._logger.error(f"Error in completion listener: {e}")
    
    async def set_error(self, error: Exception) -> None:
        """
        [Method intent]
        Mark the response as failed with an error.
        
        [Design principles]
        - Clear error reporting
        - Immediate propagation to dependent components
        
        [Implementation details]
        - Stores error information
        - Sets completion event to unblock waiting consumers
        - Does not call completion listeners (error is not completion)
        
        Args:
            error: The error that caused the failure
            
        Raises:
            StreamingError: If the response has already completed
        """
        if self.is_complete():
            raise StreamingError("Cannot set error on completed response")
        
        self._error = error
        self._complete.set()  # Unblock any waiting consumers
    
    def add_listener(self, listener: Callable[[T], None]) -> None:
        """
        [Method intent]
        Add a listener for new chunks.
        
        [Design principles]
        - Support for event-based chunk processing
        - Enable parallel processing of chunks
        
        [Implementation details]
        - Registers a callback function for new chunks
        - Listener will be called for each new chunk
        
        Args:
            listener: Callback function for new chunks
        """
        self._listeners.append(listener)
    
    def remove_listener(self, listener: Callable[[T], None]) -> None:
        """
        [Method intent]
        Remove a previously registered chunk listener.
        
        [Design principles]
        - Support for dynamic listener management
        - Clean removal of listeners when no longer needed
        
        [Implementation details]
        - Removes callback from listener list if present
        - Silently ignores removal of unregistered listeners
        
        Args:
            listener: Previously registered callback function
        """
        if listener in self._listeners:
            self._listeners.remove(listener)
    
    def add_completion_listener(self, listener: Callable[[], None]) -> None:
        """
        [Method intent]
        Add a listener for stream completion.
        
        [Design principles]
        - Support for completion-dependent operations
        - Enable clean finalization of resources
        
        [Implementation details]
        - Registers a callback function for completion
        - Listener will be called once when stream completes
        
        Args:
            listener: Callback function for completion
        """
        self._complete_listeners.append(listener)
    
    def remove_completion_listener(self, listener: Callable[[], None]) -> None:
        """
        [Method intent]
        Remove a previously registered completion listener.
        
        [Design principles]
        - Support for dynamic listener management
        - Clean removal of listeners when no longer needed
        
        [Implementation details]
        - Removes callback from completion listener list if present
        - Silently ignores removal of unregistered listeners
        
        Args:
            listener: Previously registered completion callback
        """
        if listener in self._complete_listeners:
            self._complete_listeners.remove(listener)
    
    def is_complete(self) -> bool:
        """
        [Method intent]
        Check if the response has completed.
        
        [Design principles]
        - Clear indication of stream status
        - Simple interface for completion checking
        
        [Implementation details]
        - Returns the state of the completion event
        
        Returns:
            bool: True if the response has completed, False otherwise
        """
        return self._complete.is_set() and self._error is None
    
    def has_error(self) -> bool:
        """
        [Method intent]
        Check if the response has failed with an error.
        
        [Design principles]
        - Clear indication of error status
        - Simple interface for error checking
        
        [Implementation details]
        - Checks if an error has been recorded
        
        Returns:
            bool: True if the response has failed, False otherwise
        """
        return self._error is not None
    
    def get_error(self) -> Optional[Exception]:
        """
        [Method intent]
        Get the error that caused the response to fail, if any.
        
        [Design principles]
        - Provide access to error details
        - Enable proper error handling by consumers
        
        [Implementation details]
        - Returns the stored error or None
        
        Returns:
            Optional[Exception]: The error or None if no error occurred
        """
        return self._error
    
    def get_chunks(self) -> List[T]:
        """
        [Method intent]
        Get all chunks received so far.
        
        [Design principles]
        - Provide access to all received chunks
        - Support for buffered processing
        
        [Implementation details]
        - Returns a copy of the internal chunk buffer
        
        Returns:
            List[T]: List of chunks received so far
        """
        return self._chunks.copy()
    
    async def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """
        [Method intent]
        Wait for the response to complete.
        
        [Design principles]
        - Support for synchronization with completion
        - Optional timeout for non-blocking workflows
        
        [Implementation details]
        - Uses asyncio.wait_for with the completion event
        - Returns True if completed, False if timed out
        
        Args:
            timeout: Maximum time to wait in seconds, or None to wait indefinitely
            
        Returns:
            bool: True if completed, False if timed out
            
        Raises:
            StreamingError: If the response has failed with an error
        """
        try:
            if timeout is not None:
                await asyncio.wait_for(self._complete.wait(), timeout)
            else:
                await self._complete.wait()
                
            if self._error:
                raise StreamingError(f"Response failed: {self._error}")
                
            return True
        except asyncio.TimeoutError:
            return False
    
    async def stream(self) -> AsyncIterator[T]:
        """
        [Method intent]
        Stream response chunks as they arrive.
        
        [Design principles]
        - Universal streaming interface (implements IStreamable)
        - Support for asynchronous iteration
        - Real-time access to chunks
        
        [Implementation details]
        - Yields already received chunks
        - Sets up queue for future chunks
        - Yields new chunks as they arrive
        - Completes when the response completes
        
        Yields:
            Response chunks
            
        Raises:
            StreamingError: If the response has failed
        """
        # Yield already received chunks
        for chunk in self._chunks:
            yield chunk
            
        # Set up queue for future chunks
        queue = asyncio.Queue()
        
        async def on_chunk(chunk: T):
            await queue.put(chunk)
            
        # Register chunk listener
        self.add_listener(on_chunk)
        
        try:
            while not self.is_complete():
                # Wait for more chunks or completion
                try:
                    chunk = await queue.get()
                    yield chunk
                except asyncio.CancelledError:
                    break
                    
            # Check for errors
            if self._error:
                raise StreamingError(f"Response failed: {self._error}")
        finally:
            # Clean up listener to avoid memory leaks
            self.remove_listener(on_chunk)
```

## StreamEmulator Implementation

Create a stream emulator for non-streaming models:

```python
class StreamEmulator:
    """
    [Class intent]
    Emulates streaming responses for non-streaming models by chunking their output.
    This enables a consistent streaming interface even for models or operations
    that only support synchronous completion.
    
    [Design principles]
    - Provide streaming interface compatibility for non-streaming models
    - Support chunk-by-chunk delivery (not token-by-token)
    - Control chunk size for optimal performance
    
    [Implementation details]
    - Converts synchronous response to asynchronous chunks
    - Uses configurable chunking strategy
    - Returns StreamingResponse objects for consistent interface
    """
    
    def __init__(self, 
                chunk_size: int = 100, 
                chunk_overlap: int = 0,
                delimiter: Optional[str] = None):
        """
        [Method intent]
        Initialize the stream emulator with chunking parameters.
        
        [Design principles]
        - Configurable chunking behavior
        - Support for different chunking strategies
        
        [Implementation details]
        - Stores chunking parameters for later use
        - Provides sensible defaults
        
        Args:
            chunk_size: Target size of chunks in characters
            chunk_overlap: Number of overlapping characters between chunks
            delimiter: Optional string to use as chunk delimiter
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.delimiter = delimiter
        self._logger = logging.getLogger(self.__class__.__name__)
    
    async def _chunk_text(self, text: str) -> List[Dict[str, Any]]:
        """
        [Method intent]
        Split text into chunks based on configuration.
        
        [Design principles]
        - Clean chunking based on size or delimiters
        - Support different text structures
        
        [Implementation details]
        - Uses delimiter if provided, otherwise size-based chunking
        - Handles overlap between chunks
        - Formats chunks as dictionaries for consistency
        
        Args:
            text: The text to chunk
            
        Returns:
            List[Dict[str, Any]]: List of chunks in dictionary format
        """
        chunks = []
        
        if self.delimiter:
            # Delimiter-based chunking
            parts = text.split(self.delimiter)
            for part in parts:
                if part.strip():  # Skip empty parts
                    chunks.append({"content": part, "stop_reason": None})
        else:
            # Size-based chunking
            start = 0
            while start < len(text):
                end = min(start + self.chunk_size, len(text))
                chunk_text = text[start:end]
                if chunk_text.strip():  # Skip empty chunks
                    chunks.append({"content": chunk_text, "stop_reason": None})
                start = end - self.chunk_overlap
        
        # Mark last chunk with stop reason
        if chunks:
            chunks[-1]["stop_reason"] = "end_of_text"
            
        return chunks
    
    async def emulate_stream(self, response: str) -> StreamingResponse[Dict[str, Any]]:
        """
        [Method intent]
        Emulate a streaming response from a non-streaming model.
        
        [Design principles]
        - Convert synchronous text to streaming response
        - Follow same interface as real streaming responses
        
        [Implementation details]
        - Creates StreamingResponse object
        - Chunks the input text
        - Adds chunks to the response with delays
        - Marks response as complete when done
        
        Args:
            response: Complete response text from non-streaming model
            
        Returns:
            StreamingResponse: Emulated streaming response
        """
        streaming_response = StreamingResponse()
        
        try:
            # Generate chunks from the response
            chunks = await self._chunk_text(response)
            
            # Add chunks to the streaming response
            for chunk in chunks:
                await streaming_response.add_chunk(chunk)
                # Small delay for more realistic streaming (configurable)
                await asyncio.sleep(0.01)
                
            # Complete the streaming response
            await streaming_response.complete()
        except Exception as e:
            await streaming_response.set_error(e)
            self._logger.error(f"Error in stream emulation: {e}")
            
        return streaming_response
```

## StreamTransformer Implementation

Create a stream transformer for modifying streaming responses:

```python
class StreamTransformer(Generic[T]):
    """
    [Class intent]
    Transforms chunks in a streaming response using a provided transformation function.
    This enables stream processing operations like filtering, mapping, and aggregation.
    
    [Design principles]
    - Support for stream transformation operations
    - Clean functional composition
    - Preserve streaming semantics
    
    [Implementation details]
    - Takes input stream and transformation function
    - Creates new StreamingResponse with transformed chunks
    - Handles errors in transformation
    """
    
    def __init__(self, transform_func: Callable[[T], Any]):
        """
        [Method intent]
        Initialize the transformer with a transformation function.
        
        [Design principles]
        - Function-driven transformation
        - Simple interface for common operations
        
        [Implementation details]
        - Stores transformation function for later use
        
        Args:
            transform_func: Function to apply to each chunk
        """
        self.transform_func = transform_func
        self._logger = logging.getLogger(self.__class__.__name__)
    
    async def transform(self, stream: AsyncIterator[T]) -> StreamingResponse[Any]:
        """
        [Method intent]
        Transform a stream using the provided function.
        
        [Design principles]
        - Stream transformation with error handling
        - Preserve streaming semantics
        - Support for asynchronous transformation
        
        [Implementation details]
        - Creates new StreamingResponse
        - Processes each chunk through the transform function
        - Handles errors during transformation
        
        Args:
            stream: Input async iterator of chunks
            
        Returns:
            StreamingResponse: New streaming response with transformed chunks
        """
        result = StreamingResponse()
        
        try:
            async for chunk in stream:
                try:
                    transformed_chunk = self.transform_func(chunk)
                    await result.add_chunk(transformed_chunk)
                except Exception as e:
                    await result.set_error(StreamingError(f"Error transforming chunk: {e}"))
                    self._logger.error(f"Error in transform function: {e}")
                    return result
            
            await result.complete()
        except Exception as e:
            await result.set_error(StreamingError(f"Error processing stream: {e}"))
            self._logger.error(f"Error processing stream: {e}")
            
        return result
```

## StreamCombiner Implementation

Create a stream combiner for merging multiple streams:

```python
class StreamCombiner(Generic[T]):
    """
    [Class intent]
    Combines multiple streams into a single stream.
    This enables parallel processing streams to be merged into a unified output.
    
    [Design principles]
    - Support for stream composition
    - Parallel processing of multiple sources
    - Consistent ordering options
    
    [Implementation details]
    - Takes multiple input streams
    - Creates new StreamingResponse with combined chunks
    - Support for different combination strategies
    """
    
    async def combine(self, 
                     streams: List[AsyncIterator[T]], 
                     ordered: bool = False) -> StreamingResponse[T]:
        """
        [Method intent]
        Combine multiple streams into a single stream.
        
        [Design principles]
        - Support for both ordered and unordered combination
        - Clean handling of multiple async iterators
        - Error propagation from any stream
        
        [Implementation details]
        - Creates new StreamingResponse
        - Uses gather for parallel processing if not ordered
        - Uses chain for sequential processing if ordered
        - Propagates errors from any stream
        
        Args:
            streams: List of input streams
            ordered: Whether to preserve order across streams
            
        Returns:
            StreamingResponse: Combined streaming response
        """
        result = StreamingResponse()
        
        async def process_stream(stream):
            try:
                async for chunk in stream:
                    await result.add_chunk(chunk)
            except Exception as e:
                await result.set_error(StreamingError(f"Error in stream: {e}"))
                return False
            return True
        
        try:
            if ordered:
                # Process streams in order
                for stream in streams:
                    success = await process_stream(stream)
                    if not success:
                        return result
            else:
                # Process streams in parallel
                tasks = [process_stream(stream) for stream in streams]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Check for errors
                for res in results:
                    if isinstance(res, Exception):
                        await result.set_error(StreamingError(f"Error in parallel stream: {res}"))
                        return result
                    elif res is False:
                        # Error already set by process_stream
                        return result
            
            await result.complete()
        except Exception as e:
            await result.set_error(StreamingError(f"Error combining streams: {e}"))
            
        return result
```

## Implementation Steps

1. **Core Streaming Response**
   - Implement `StreamingResponse` class in `src/dbp/llm/common/streaming.py`
   - Ensure proper AsyncIO integration with event handling
   - Add comprehensive error handling

2. **Stream Emulation**
   - Create `StreamEmulator` class for non-streaming models
   - Implement configurable chunking strategies
   - Ensure consistent interface with real streaming

3. **Stream Transformation**
   - Implement `StreamTransformer` for modifying streams
   - Create functional composition patterns
   - Add error handling for transformations

4. **Stream Combination**
   - Create `StreamCombiner` for merging streams
   - Support both ordered and unordered combination
   - Implement parallel processing with proper error handling

## Notes

- The streaming implementation is built around AsyncIO for non-blocking operation
- All components follow the project's "throw on error" approach
- Streaming is implemented at the chunk level (not token level) as specified
- The implementation supports both real streaming and emulated streaming
- Stream transformation and combination enable complex streaming workflows

## Next Steps

After completing this phase:
1. Proceed to Phase 4 (Prompt Management)
2. Implement prompt loading and template substitution
3. Create the prompt caching system
