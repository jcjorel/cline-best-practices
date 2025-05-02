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
# This file provides AsyncIO-based streaming interfaces for LLM interactions.
# It defines abstractions for handling streaming responses from LLM models in
# an asynchronous manner, supporting both token-level and chunk-level streaming.
###############################################################################
# [Source file design principles]
# - All streaming interfaces follow AsyncIO patterns for non-blocking operations
# - Chunk-based streaming is the primary interface for consistency across models
# - Provides emulation layers for non-streaming models when needed
# - Clean separation between streaming protocol and model-specific implementations
# - Error propagation follows the "raise on error" principle with no fallbacks
###############################################################################
# [Source file constraints]
# - Must be compatible with AsyncIO event loop
# - Must support both real streaming and emulated streaming for non-streaming models
# - Must handle connection interruptions and timing constraints appropriately
# - Storage of full response for post-processing is model-dependent
###############################################################################
# [Dependencies]
# codebase:src/dbp/llm/common/exceptions.py
# codebase:src/dbp/llm/common/base.py
# system:asyncio
# system:typing
###############################################################################
# [GenAI tool change history]
# 2025-05-02T10:30:00Z : Initial creation for LangChain/LangGraph integration by CodeAssistant
# * Created streaming interfaces for AsyncIO-based LLM interactions
###############################################################################

"""
Asynchronous streaming interfaces for LLM interactions.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, List, Optional, TypeVar, Generic, Any, Union

from .exceptions import StreamingError, StreamingTimeoutError

T = TypeVar('T')

class StreamingResponse(Generic[T]):
    """
    [Class intent]
    Base class for streaming responses from LLMs, providing access to both 
    incremental chunks and the complete response.
    
    [Design principles]
    Provides a consistent interface for accessing streaming content regardless
    of the underlying LLM implementation. Allows tracking of both the full
    response and access to the stream of individual chunks.
    
    [Implementation details]
    Implements storage of the complete response for models that don't track it
    internally. Provides a unified interface for both streaming and 
    non-streaming LLMs.
    """
    
    def __init__(self):
        """
        [Class method intent]
        Initializes a new streaming response container.
        
        [Design principles]
        Creates a minimally initialized object with collections that will
        gather streaming chunks.
        
        [Implementation details]
        Initializes empty collections to store the full response.
        """
        self._finished = False
        self._chunks: List[T] = []
    
    @property
    def is_complete(self) -> bool:
        """
        [Class method intent]
        Returns true if the streaming response is complete.
        
        [Design principles]
        Provides a simple flag to check streaming state.
        
        [Implementation details]
        Returns the internal _finished flag.
        """
        return self._finished
    
    def append_chunk(self, chunk: T) -> None:
        """
        [Class method intent]
        Adds a new chunk to this streaming response.
        
        [Design principles]
        Updates internal state with new streaming content.
        
        [Implementation details]
        Adds the chunk to the internal chunks list and performs
        any necessary model-specific processing.
        """
        if self._finished:
            raise StreamingError("Cannot append to a completed stream")
        self._chunks.append(chunk)
    
    def mark_complete(self) -> None:
        """
        [Class method intent]
        Marks this streaming response as complete.
        
        [Design principles]
        Finalizes the streaming response state.
        
        [Implementation details]
        Sets the finished flag to True to indicate completion of streaming.
        """
        self._finished = True
    
    @property
    def chunks(self) -> List[T]:
        """
        [Class method intent]
        Returns all chunks received so far.
        
        [Design principles]
        Provides access to raw streaming content.
        
        [Implementation details]
        Returns a copy of the internal chunks list to prevent modification.
        """
        return self._chunks.copy()


class TextStreamingResponse(StreamingResponse[str]):
    """
    [Class intent]
    Specialized streaming response for text-based LLMs that handles
    text chunks.
    
    [Design principles]
    Optimized for text streaming with appropriate aggregation methods.
    
    [Implementation details]
    Extends StreamingResponse for string types and adds text-specific
    functionality like joining chunks into a complete text.
    """
    
    @property
    def text(self) -> str:
        """
        [Class method intent]
        Returns the complete text response by joining all chunks.
        
        [Design principles]
        Provides easy access to the full text response.
        
        [Implementation details]
        Joins all text chunks into a single string.
        """
        return "".join(self.chunks)
    
    def __str__(self) -> str:
        """
        [Class method intent]
        Returns string representation of this response.
        
        [Design principles]
        Makes the class easier to use in string contexts.
        
        [Implementation details]
        Returns the complete text response.
        """
        return self.text


class IStreamable(ABC):
    """
    [Class intent]
    Interface for objects that support streaming response generation.
    
    [Design principles]
    - Establish a common interface for all streaming operations
    - Allow unified handling of different streaming sources
    
    [Implementation details]
    - Abstract base class with a single required method
    - Simple interface that can be implemented by various components
    """
    
    @abstractmethod
    async def stream(self) -> AsyncGenerator[T, None]:
        """
        [Class method intent]
        Returns an asynchronous generator that yields chunks of content.
        
        [Design principles]
        Provides stream access using standard Python AsyncIO patterns.
        
        [Implementation details]
        Implementation depends on the specific streaming source, but must
        yield chunks as they become available.
        """
        raise NotImplementedError("Subclasses must implement stream()")


class AsyncTextStreamProvider(IStreamable):
    """
    [Class intent]
    Specialized async stream provider for text content.
    
    [Design principles]
    Provides a streaming interface specifically for text-based content
    with appropriate text handling.
    
    [Implementation details]
    Extends AsyncStreamProvider with text-specific functionality.
    """
    
    @abstractmethod
    async def stream(self) -> AsyncGenerator[str, None]:
        """
        [Class method intent]
        Returns an asynchronous generator that yields chunks of text.
        
        [Design principles]
        Provides stream access using standard Python AsyncIO patterns.
        
        [Implementation details]
        Must be implemented by subclasses to yield text chunks.
        """
        raise NotImplementedError("Subclasses must implement stream()")
    
    async def collect_streaming_response(
        self, timeout: Optional[float] = None
    ) -> TextStreamingResponse:
        """
        [Class method intent]
        Collects the entire streaming response into a TextStreamingResponse object.
        
        [Design principles]
        Provides a convenient way to gather all streaming content into
        a unified response object with timeout protection.
        
        [Implementation details]
        Iterates through the stream, collecting chunks until completion
        or timeout, then returns a complete TextStreamingResponse.
        """
        response = TextStreamingResponse()
        try:
            if timeout is not None:
                # Set a timeout for the entire streaming operation
                async with asyncio.timeout(timeout):
                    async for chunk in self.stream():
                        response.append_chunk(chunk)
            else:
                # No timeout specified, collect all chunks
                async for chunk in self.stream():
                    response.append_chunk(chunk)
                    
        except asyncio.TimeoutError:
            raise StreamingTimeoutError(f"Streaming timed out after {timeout} seconds")
        except Exception as e:
            # Preserve the original error and wrap it in StreamingError
            raise StreamingError(f"Error during streaming: {str(e)}") from e
        finally:
            # Always mark the response as complete, even if we exit due to an error
            response.mark_complete()
            
        return response


class EmulatedTextStreamProvider(AsyncTextStreamProvider):
    """
    [Class intent]
    Provides an emulated streaming experience for non-streaming LLM responses
    by breaking them into chunks.
    
    [Design principles]
    Creates a consistent streaming interface even when the underlying model
    doesn't support streaming natively.
    
    [Implementation details]
    Takes a complete text response and emulates streaming by yielding chunks
    with configurable delay to simulate realistic streaming behavior.
    """
    
    def __init__(
        self, 
        text: str, 
        chunk_size: int = 4, 
        delay: float = 0.01
    ):
        """
        [Class method intent]
        Initializes an emulated text stream from a complete text response.
        
        [Design principles]
        Configurable chunking and timing for realistic streaming simulation.
        
        [Implementation details]
        Stores the text and parameters for streaming emulation.
        
        Args:
            text: The complete text to stream
            chunk_size: Number of characters per chunk
            delay: Delay between chunks in seconds
        """
        self.text = text
        self.chunk_size = chunk_size
        self.delay = delay
    
    async def stream(self) -> AsyncGenerator[str, None]:
        """
        [Class method intent]
        Emulates a streaming response by yielding chunks of the complete text.
        
        [Design principles]
        Creates a realistic streaming experience even when the underlying
        LLM doesn't support streaming.
        
        [Implementation details]
        Splits the text into chunks and yields them with configurable delay.
        """
        for i in range(0, len(self.text), self.chunk_size):
            chunk = self.text[i:i + self.chunk_size]
            yield chunk
            if self.delay > 0:
                await asyncio.sleep(self.delay)


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
                delimiter: Optional[str] = None,
                delay: float = 0.01):
        """
        [Class method intent]
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
            delay: Delay between chunks in seconds
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.delimiter = delimiter
        self.delay = delay
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def _chunk_text(self, text: str) -> List[Dict[str, Any]]:
        """
        [Class method intent]
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
    
    async def emulate_stream(self, response: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        [Class method intent]
        Emulate a streaming response from a non-streaming model.
        
        [Design principles]
        - Convert synchronous text to streaming format
        - Follow same interface as real streaming responses
        
        [Implementation details]
        - Chunks the input text
        - Yields chunks with optional delays
        - Similar format to real streaming responses
        
        Args:
            response: Complete response text from non-streaming model
            
        Yields:
            Dict[str, Any]: Chunks formatted like streaming responses
        """
        try:
            # Generate chunks from the response
            chunks = await self._chunk_text(response)
            
            # Yield chunks with delay
            for chunk in chunks:
                yield chunk
                # Small delay for more realistic streaming
                if self.delay > 0:
                    await asyncio.sleep(self.delay)
                    
        except Exception as e:
            self.logger.error(f"Error in stream emulation: {e}")
            raise StreamingError(f"Error emulating stream: {str(e)}") from e


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
    - Creates new async generator with transformed chunks
    - Handles errors in transformation
    """
    
    def __init__(self, transform_func: Callable[[T], Any]):
        """
        [Class method intent]
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
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def transform(self, stream: AsyncGenerator[T, None]) -> AsyncGenerator[Any, None]:
        """
        [Class method intent]
        Transform a stream using the provided function.
        
        [Design principles]
        - Stream transformation with error handling
        - Preserve streaming semantics
        - Support for asynchronous transformation
        
        [Implementation details]
        - Processes each chunk through the transform function
        - Handles errors during transformation
        
        Args:
            stream: Input async generator of chunks
            
        Yields:
            Any: Transformed chunks
        """
        try:
            async for chunk in stream:
                try:
                    transformed_chunk = self.transform_func(chunk)
                    yield transformed_chunk
                except Exception as e:
                    self.logger.error(f"Error in transform function: {e}")
                    raise StreamingError(f"Error transforming chunk: {str(e)}") from e
                    
        except Exception as e:
            if not isinstance(e, StreamingError):
                self.logger.error(f"Error processing stream: {e}")
                raise StreamingError(f"Error processing stream: {str(e)}") from e
            raise


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
    - Creates new async generator with combined chunks
    - Support for different combination strategies
    """
    
    def __init__(self):
        """
        [Class method intent]
        Initialize the stream combiner.
        
        [Design principles]
        - Simple initialization
        
        [Implementation details]
        - Sets up logging for error tracking
        """
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def combine(self, 
                     streams: List[AsyncGenerator[T, None]], 
                     ordered: bool = False) -> AsyncGenerator[T, None]:
        """
        [Class method intent]
        Combine multiple streams into a single stream.
        
        [Design principles]
        - Support for both ordered and unordered combination
        - Clean handling of multiple async iterators
        - Error propagation from any stream
        
        [Implementation details]
        - Uses gather for parallel processing if not ordered
        - Uses sequential processing if ordered
        - Propagates errors from any stream
        
        Args:
            streams: List of input streams
            ordered: Whether to preserve order across streams
            
        Yields:
            T: Combined stream chunks
        """
        if ordered:
            # Process streams in order (sequential)
            for stream in streams:
                try:
                    async for chunk in stream:
                        yield chunk
                except Exception as e:
                    self.logger.error(f"Error in ordered stream: {e}")
                    if not isinstance(e, StreamingError):
                        raise StreamingError(f"Error in ordered stream: {str(e)}") from e
                    raise
        else:
            # Process streams in parallel using asyncio.as_completed
            # Create tasks for each stream
            pending = set()
            
            # Helper to process a single stream
            async def process_stream(stream):
                try:
                    async for chunk in stream:
                        yield chunk
                except Exception as e:
                    self.logger.error(f"Error in parallel stream: {e}")
                    if not isinstance(e, StreamingError):
                        raise StreamingError(f"Error in parallel stream: {str(e)}") from e
                    raise
                    
            # Start all streams
            for stream in streams:
                task = asyncio.create_task(process_stream(stream).__anext__())
                pending.add(task)
                
            # Process results as they complete
            while pending:
                done, pending = await asyncio.wait(
                    pending, 
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                for task in done:
                    try:
                        result = task.result()
                        yield result
                        
                        # Queue up the next chunk from this stream
                        stream_idx = streams.index(task._coro.cr_frame.f_locals['self'])
                        next_task = asyncio.create_task(process_stream(streams[stream_idx]).__anext__())
                        pending.add(next_task)
                    except StopAsyncIteration:
                        # This stream is exhausted
                        pass
                    except Exception as e:
                        # Propagate errors
                        self.logger.error(f"Error in parallel stream: {e}")
                        if not isinstance(e, StreamingError):
                            raise StreamingError(f"Error in parallel stream: {str(e)}") from e
                        raise
