# LangChain Integration with Bedrock

This document describes how to integrate LangChain with AWS Bedrock using the `BedrockClientFactory`.

## Overview

The `BedrockClientFactory.create_langchain_chatbedrock()` method creates a LangChain `ChatBedrockConverse` instance that leverages our model discovery system to find the optimal region and configuration for any Bedrock model.

## Key Benefits

- **Automatic Region Selection**: Uses our model discovery system to find the best available region
- **Inference Profile Handling**: Automatically extracts region from inference profile ARNs
- **Efficient Client Creation**: Uses AWSClientFactory for properly configured boto3 clients
- **Standard LangChain Patterns**: Works seamlessly with LangChain's messaging system

## Basic Usage

```python
from dbp.llm.bedrock.client_factory import BedrockClientFactory
from langchain_core.messages import SystemMessage, HumanMessage

# Create a LangChain chat model
chat_model = BedrockClientFactory.create_langchain_chatbedrock(
    model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",
    use_model_discovery=True,
    streaming=True
)

# Create messages using standard LangChain pattern
messages = [
    SystemMessage(content="You are a helpful assistant."),
    HumanMessage(content="Hello!")
]

# Stream the response
async for chunk in chat_model.astream(messages):
    print(chunk.content, end="", flush=True)
```

## Advanced Usage: Conversation Chain

```python
from dbp.llm.bedrock.client_factory import BedrockClientFactory
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# Create a LangChain chat model
chat_model = BedrockClientFactory.create_langchain_chatbedrock(
    model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",
    use_model_discovery=True,
    streaming=True
)

# Create a conversation prompt template
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful AI assistant."),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}")
])

# Create memory to store conversation history
memory = ConversationBufferMemory(return_messages=True)

# Create the conversation chain
conversation = ConversationChain(
    llm=chat_model,
    prompt=prompt,
    memory=memory
)

# Use the conversation chain
response = await conversation.ainvoke({"input": "Hello, who are you?"})
print(response["response"])
```

## Parameter Reference

| Parameter | Description | Default |
|-----------|-------------|---------|
| `model_id` | The Bedrock model ID | Required |
| `region_name` | AWS region name | Auto-selected if not provided |
| `profile_name` | AWS profile name | None |
| `credentials` | Explicit AWS credentials | None |
| `max_retries` | Maximum API retries | 3 |
| `timeout` | Connection timeout in seconds | 30 |
| `logger` | Custom logger | None |
| `use_model_discovery` | Use model discovery for region selection | True |
| `preferred_regions` | List of preferred regions | None |
| `inference_profile_arn` | Inference profile ARN | None |
| `streaming` | Enable response streaming | True |

## Error Handling

The method raises various exceptions to ensure clear error messages:

- `UnsupportedModelError`: When the model ID is not supported by the project
- `ConfigurationError`: When required configuration is missing or invalid
- `ImportError`: When langchain_aws is not installed
- `LLMError`: For other client creation failures

Always handle these exceptions appropriately in your code.

## AWS Client Factory Integration

The LangChain integration uses our `AWSClientFactory` to create properly configured boto3 clients. This provides several advantages:

1. **Client Caching**: Reuses clients for the same service and region
2. **Standardized Configuration**: Applies appropriate timeouts and retries
3. **Consistent Credentials**: Handles AWS credentials consistently
4. **Error Handling**: Provides clear error messages for AWS API errors

The integration automatically configures the boto3 client with appropriate settings for AI model inference, including increased read timeouts.

## Advanced Topics

### Inference Profile Handling

If you provide an `inference_profile_arn`, the method will:

1. Extract the region from the ARN (format: `arn:aws:bedrock:REGION:account-id:...`)
2. Override any explicitly provided region with the one from the ARN
3. Include the inference profile ARN in the request parameters

### Performance Optimization

For optimal performance:

1. **Preselect Regions**: If calling multiple times with the same model, use `get_best_regions_for_model()` once and reuse the region
2. **Disable Discovery**: Set `use_model_discovery=False` when providing an explicit region
3. **Batch Requests**: When possible, send multiple messages in a single request

## Related Examples

For more examples, see:
- `src/dbp/llm/bedrock/examples/langchain_client_factory_example.py` - Basic usage examples
- `src/dbp/llm/bedrock/examples/langchain_model_discovery_optimized.py` - Performance optimized examples
