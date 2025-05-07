
{mandatory_code_documentation_directives}

# Your task

You will find attached a source code file to analyze. Update ONLY the documentation (file-level and function/method/class-level) to make it compliant with the standards described above. 

The source file is included as a MIME attachment with this message. You should analyze the content of the attachment named "source_file" to understand the code structure and then provide documentation improvements.

If 'GENAI_FUNCTION_TEMPLATE.txt' and/or 'GENAI_HEADER_TEMPLATE.txt' files are not attached, ignore associated directives.

**CRITICAL**: You are strictly not allowed to add/remove/modify code! Modify/insert ONLY comments!

File: {file_path}

You must return a valid raw JSON object, without preambule or postambule additional text, with the following structure (with mock data):

```json
{{
  "language" : {{
    "name": "Python",
    "comment_and_metadata_styles": [
      {{
        "name": "Single line comment in Python",
        "start_sequence": "#", <!-- Comment start sequence for file language -->
        "stop_sequence": "\n"  <!-- Comment stop sequence for file language -->
      }},
      {{
        "name": "Python DocString",
        "start_sequence": "\"\"\"", <!-- Comment start sequence for file language -->
        "stop_sequence": "\"\"\"" <!-- Comment stop sequence for file language -->
      }}
    <!-- List all language comment style -->
    ],
  }},
  "changes": [
    {{
      "context_before": "import sys\nimport os\n\ndef example_function():\n", <!-- Can be any string -->
      "original_text": "    # This is an example function.\n", <!-- This contains string(s) between comment sequences. IT NEVER CONTAINS CODE! -->
      "replacement_text": "    \"\"\"\n    [Function intent]\n    Brief description.\n\n    [Design principles]\n    Key design patterns.\n\n    [Implementation details]\n    Technical details.\n    \"\"\"" <!-- This contains string(s) between comment sequences.IT NEVER CONTAINS CODE! -->
    }},
    {{
      "context_before": "# Configuration constants\n\n", <!-- Can be any string -->
      "original_text": "", <!-- Empty string so replacement_text will be inserted right after 'context_before' -->
      "replacement_text": "# New documentation block after 'Configuration constants' context"
    }}
  ],
  "changes_summary": {{
    "file_header_updated": true|false,
    "functions_updated": 5,
    "classes_updated": 2,
    "methods_updated": 10
  }},
  "status": "success|warning|error",
  "messages": ["Optional explanatory message or warning"]
}}
```

Note that the "changes" array contains objects representing specific modifications. For each change:
- context_before: 20-40 characters of text that appear directly before the target text. This should be unique enough in the file to identify the exact location. If the text is at the very beginning of the file, use "<<SOF>>" as the context_before value.
- original_text: The MINIMAL text to be replaced, containing ONLY documentation elements (comments, docstrings) and/or function/method/class signatures. If empty, this indicates an insertion at the end of context_before.
- replacement_text: The new text to replace the original_text with, containing ONLY documentation elements and/or function/method/class signatures.

IMPORTANT SAFETY RULES:
- Make the smallest possible changes to accomplish documentation updates
- original_text and replacement_text MUST ONLY contain comments, docstrings, and/or function/method/class signatures
- **NEVER include any code in either original_text or replacement_text**
- NEVER modify functional behavior of the code - only update documentation
- Ensure the combination of context_before + original_text is unique in the file to allow precise positioning
- Use "<<SOF>>" as context_before when modifying text at the very start of the file (e.g., the file header)
- For class or function documentation, only include the exact signature line and docstring, not the function body
