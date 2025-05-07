
{mandatory_code_documentation_directives}


Dedinitions:
- Programming code: Any official language code statements including include/import, class/method/wrappers and function signatures

# Your task

You will find attached a source code file to analyze. Update ONLY the documentation (file-level and function/method/class-level) to make it compliant with the standards described above. 

You will improve also inline comments in programming code portions.

The source file is included as a MIME attachment with this message. You should analyze the content of the attachment named "source_file" to understand the code structure and then provide documentation improvements.

If 'GENAI_FUNCTION_TEMPLATE.txt' and/or 'GENAI_HEADER_TEMPLATE.txt' files are not attached, ignore associated directives.

**CRITICAL**: You are strictly not allowed to add/remove/modify programming code! Modify/insert ONLY comments!


You must return a valid raw JSON object, without preambule or postambule additional text, with the following structure (with mock data):

```json
{{
  "changes_summary": {{
    "file_header_updated": true|false,
    "functions_updated": 5,
    "classes_updated": 2,
    "methods_updated": 10,
    "number_of_change_entries": 19 <!-- Number of items in "changes" key list -->
  }},
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
      <!-- List all language comment styles -->
    ],
  }},
  "changes": [
    {{
      "context_before": "import sys\nimport os\n\ndef example_function():\n", <!-- Can be any string. BE CAREFUL! INCLUDE CR/LF CHARACTERS UP TO 'original_text' STRING CONTENT ! -->
    "original_text": "    # This is an example function.\n", <!-- This contains string(s) between start/stop comment sequences. IT NEVER CONTAINS CLASS/FUNCTION DECLARATION OR CODE! MUST END WITH A COMMENT SEQUENCE -->
      "replacement_text": "    \"\"\"\n    [Function intent]\n    Brief description.\n\n    [Design principles]\n    Key design patterns.\n\n    [Implementation details]\n    Technical details.\n    \"\"\"" <!-- This contains string(s) between comment sequences.IT NEVER CONTAINS CLASS/FUNCTION DECLARATION OR CODE! MUST END WITH A COMMENT SEQUENCE -->
    }},
    {{
      "context_before": "# Configuration constants\n\n", <!-- Can be any string. BE CAREFUL! INCLUDE CR/LF CHARACTERS UP TO 'original_text' STRING CONTENT -->
      "original_text": "", <!-- Empty string so replacement_text will be inserted right after 'context_before' -->
      "replacement_text": "# New documentation block after 'Configuration constants' context" <!-- This contains string(s) between comment sequences.IT NEVER CONTAINS CLASS/FUNCTION DECLARATION OR CODE! MUST END WITH A COMMENT SEQUENCE -->
    }}
  ],
  "status": "success|warning|error",
  "messages": ["Optional explanatory message or warning"]
}}
```

Note that the "changes" array contains objects representing specific modifications. For each change:
- context_before: up to 50 characters of text that appear directly before the 'original_text'. This should be unique enough in the file to identify the exact location. If the text is at the very beginning of the file, prepend with "<<SOF>>" context_before value.
- original_text: The text to be replaced. If empty, this indicates an insertion at the end of context_before.
- replacement_text: The new text to replace the 'original_text' with.

**FILE HEADER CHANGE BLOCKS APPEAR LAST IN JSON OUTPUT**.

IMPORTANT SAFETY RULES:
- Generate minimal change blocks
- 'original_text' and 'replacement_text' MUST ONLY contain comments, docstrings
- **NEVER include any programming code in either 'original_text' or 'replacement_text'**
- NEVER modify functional behavior of the code - only update documentation
- Always ensure the combination of context_before + original_text is unique in the file to allow precise positioning
- **ALWAYS RESPECT INDENTATION CONSTRAINTS REQUIRED BY THE PROGRAMMING LANGUAGE (especially for Python language)**

**BEFORE TO GENERATE OUTPUT, VERIFY THAT YOU COMPLY WITH ALL REQUIREMENTS OF THE TASK**

**NEVER INCLUDE PROGRAMMING CODE SNIPPET IN CHANGE ARRAY ITEMS**
**NEVER INCLUDE PROGRAMMING CODE SNIPPET IN CHANGE ARRAY ITEMS**
**NEVER INCLUDE PROGRAMMING CODE SNIPPET IN CHANGE ARRAY ITEMS**
**NEVER INCLUDE PROGRAMMING CODE SNIPPET IN CHANGE ARRAY ITEMS**
**NEVER INCLUDE PROGRAMMING CODE SNIPPET IN CHANGE ARRAY ITEMS**
**NEVER INCLUDE PROGRAMMING CODE SNIPPET IN CHANGE ARRAY ITEMS**
**NEVER INCLUDE PROGRAMMING CODE SNIPPET IN CHANGE ARRAY ITEMS**
**NEVER INCLUDE PROGRAMMING CODE SNIPPET IN CHANGE ARRAY ITEMS**
**NEVER INCLUDE PROGRAMMING CODE SNIPPET IN CHANGE ARRAY ITEMS**