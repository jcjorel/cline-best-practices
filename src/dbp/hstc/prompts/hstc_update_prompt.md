# Hierarchical Semantic Tree Context (HSTC)

- **Purpose**: Documents how the project IS actually implemented (descriptive)
- **Focus**: Current codebase structure, file purposes, implementation details
- **Authority**: Serves as the authoritative source for implementation context
- **Key Files**: HSTC.md files distributed throughout the directory hierarchy

You will find below information about a directory and its contents. Your task is to create or update the HSTC.md file for this directory.

Directory: {directory_name}

## Source Files:
{files_json_data}

## Child Directories:
{child_directories_json_data}

## Existing HSTC.md (if available):
{existing_hstc_content}

You must return a valid JSON object with the following structure:

```json
{
  "hstc_content": {
    "directory_name": "name of this directory",
    "directory_purpose": "detailed description of this directory's purpose",
    "child_directories": [
      {
        "name": "child_directory_name",
        "purpose": "description of child directory purpose"
      }
    ],
    "files": [
      {
        "name": "filename.ext",
        "source_file_intent": "content of source file intent section",
        "source_file_design_principles": "content of design principles section",
        "source_file_constraints": "content of constraints section",
        "dependencies": [
          {"kind": "codebase|system|other", "dependency": "dependency path"}
        ],
        "change_history": [
          {
            "timestamp": "YYYY-MM-DDThh:mm:ssZ",
            "summary": "change summary",
            "details": ["change detail 1", "change detail 2"]
          }
        ]
      }
    ]
  },
  "status": "success|warning|error",
  "messages": ["Optional explanatory message or warning"]
}
```
