# Coordinator Query Classifier Prompt

## System Instructions

Analyze the user query and context below. Determine which of the available internal tools are needed to fulfill the request.
Output a JSON list of tool calls, including the 'tool_name' and necessary 'parameters' for each call.
If no tools are needed, output an empty JSON list [].

## Input Format

### User Query
{query}

### Context
{context}

### Parameters Provided
{parameters}

### Available Internal Tools
{available_tools}

## Output Format

REQUIRED TOOL CALLS (JSON List):
