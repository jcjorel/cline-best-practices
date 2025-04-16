# Metadata Extraction Prompt

## System Instructions

Analyze the following source code file and extract metadata based on the provided JSON schema. Focus on documentation within header comments and docstrings. Infer the programming language.

## Input Format

### File Path
{file_path}

### File Extension
{file_extension}

## Source Code
```
{file_content}
```

## Expected Output Schema

The metadata should be extracted and formatted according to the following JSON schema:

```json
{
  "path": "string (should match input file_path)",
  "language": "string (e.g., 'Python', 'JavaScript', 'Java')",
  "headerSections": {
    "intent": "string | null",
    "designPrinciples": ["string"],
    "constraints": ["string"],
    "referenceDocumentation": ["string"],
    "changeHistory": [
      {
        "timestamp": "string (ISO8601 format, e.g., YYYY-MM-DDTHH:MM:SSZ) | null",
        "summary": "string | null",
        "details": ["string"]
      }
    ]
  },
  "functions": [
    {
      "name": "string",
      "docSections": {
        "intent": "string | null",
        "designPrinciples": ["string"],
        "implementationDetails": "string | null",
        "designDecisions": "string | null"
      },
      "parameters": ["string"],
      "lineRange": {"start": "number | null", "end": "number | null"}
    }
  ],
  "classes": [
    {
      "name": "string",
      "docSections": {
        "intent": "string | null",
        "designPrinciples": ["string"],
        "implementationDetails": "string | null",
        "designDecisions": "string | null"
      },
      "methods": [
        {
          "name": "string",
          "docSections": {
            "intent": "string | null",
            "designPrinciples": ["string"],
            "implementationDetails": "string | null",
            "designDecisions": "string | null"
          },
          "parameters": ["string"],
          "lineRange": {"start": "number | null", "end": "number | null"}
        }
      ],
      "lineRange": {"start": "number | null", "end": "number | null"}
    }
  ]
}
```

## Output Format

EXTRACTED METADATA (JSON format):
