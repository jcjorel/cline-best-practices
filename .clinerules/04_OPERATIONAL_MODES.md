# Operational Modes and Special Commands

## CRITICAL: Mandatory action at every session start

**CRITICAL: At first interaction of a new conversation, WHATEVER THE USER REQUEST, you WILL ALWAYS read all pages returned by script "python3 coding_assistant/scripts/get_design_mode_context.py --include-top-tier-documents --include-hstc-documents --page-number [0..n]". This script returns the documents in a MIME type message. You will discover the total number of available pages in page zero message payload**

## Operational Modes
- **ACT mode (DEFAULT)**: Directly implement requested code changes
- **PLAN mode**: Create implementation plans without modifying production code
  - **Automatic PLAN mode triggers** (in priority order):
    1. User explicitly types "PLAN" or "plan this" anywhere in their request
    2. User says "Do your magic" (see special command section)
    3. Implementation meets ANY of these complexity criteria:
       - Changes required across 3+ files
       - Creation of new architectural components
       - Database schema modifications
       - Implementation exceeding 100 lines of code
- **DESIGN mode**: Special operational mode for documentation-focused work
  - Activated by command: "Enter DESIGN mode"
  - Deactivated by command: "Exit DESIGN mode"
  - When active:
    - Automatically implies PLAN mode (no direct documentation modifications until agreed by the user)
    - Restricts scope to ONLY files in `<project_root>/doc/` directory
    - Automatically reads all additional documentation files for proper context initialization through execution of script "python3 coding_assistant/scripts/get_design_mode_context.py --include-second-tier-documents --page-number [0..n]". This script returns the documents in a MIME type message. You will discover the total number of available pages in page zero message payload
    - All user requests processed in this context until explicitly exited
    - **Maintain absolute documentation consistency with each change as this is a critical goal in DESIGN mode.**
    - **Avoid documentation redundancy to prevent inconsistencies, which may require documentation refactoring even for small changes. Request user acknowledgment before implementing large refactoring efforts.**
    - **In DESIGN mode, disregard VScode visible files and VScode tabs as indicators for the work to perform.**
    - After reading core files,
      1. Check if there are pending design decisions in DESIGN_DECISIONS.md and proactively propose: "I notice there are design decisions pending integration. Would you like me to propose merging them into the appropriate documentation files?"
      2. Check if there is any HSTC_REQUIRES_UPDATE.md file in the codebase and proactively propose: "I notice there are pending HSTC updates. It is strongly advised to process them for best LLM performance. Would you like me to update pending HSTC files?
  - When exited:
    - Returns to ACT mode (default)
    - Removes scope restriction

## Special Command: "Do your magic"
When user types "Do your magic", initiate a compliance analysis:
- Default scope: Currently displayed file in editor
- Custom scope: Files/directories listed after command (e.g., "Do your magic src/components/auth")

Respond with exactly:
```
ENTERING MAGIC MODE 😉! Performing deep-dive analysis on system prompt...

[COMPLIANCE ANALYSIS: {scope}]
- Checking strict respect to documentation standards...
- Checking that source file intent reflects functions/class/methods intents
- Analyzing code structure against design principles...
- Checking code cyclomatic complexity...
- Assessing code maintainability... 
- Verifying documentation references relevance...
{detailed findings with specific line references}
{recommendations for improving compliance}
```
After completing the deep-dive analysis, present a prioritized list of remediation actions and explicitly ask for user confirmation before implementing any of the recommendations.

## Special Command: "Capture our chat"
When a user request includes the phrase "capture our chat":
1. Create a markdown file at the following path:
   ```
   <project_root>/coding_assistant/captured_chats/<date as YYYYMMDD-HHmm>-<Chat_topic_in_snake_case>.md
   ```
   Where:
   - `<date as YYYYMMDD-HHmm>` is the current date and time in the specified format
   - `<Chat_topic_in_snake_case>` is a brief descriptive name of the conversation topic
   
2. In this file, dump the complete current conversation, but highlighting the user conversation part with a YAML distinctive code block
   - Include your reasoning in the conversation dump if any
     
   **ALWAYS end properly a captured chat with the final task completion result once known and with the message "End of chat capture" message**

4. If the user has previously requested "capture our chat" in the SAME conversation:
   - ALWAYS recreate a new markdown file with an updated date

5. After creating or updating the file,
   - Stop immediatly to update the file and forget about call of this command.

## Communication Guidelines

- Always provide concrete, executable code examples rather than abstract suggestions or pseudo-code
- When presenting code snippets exceeding 50 lines, include only the most relevant sections with clear indication of omitted parts
- Document design decisions only when the user explicitly requests this documentation
- **Make heavy usage of mermaid diagrams to make clearer your recommendations, solutions, plans, proposals etc...** 
- **ALWAYS USE THE SAME SPOKEN LANGUAGE AS THE USER**
