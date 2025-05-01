# Documentation-First Workflow

## Initial Context Gathering

**CRITICAL**: On EVERY new conversational session, to get proper project context and because they are all related to each others, you MUST read these documents in this exact order BEFORE implementing changes:
1. `<project_root>/coding_assistant/GENAI_HEADER_TEMPLATE.txt` (check once per session)
2. `<project_root>/coding_assistant/GENAI_FUNCTION_TEMPLATE.txt` (check once per session)
3. `<project_root>/doc/DESIGN.md` for architectural principles
4. `<project_root>/doc/DESIGN_DECISIONS.md` for recent design decisions not yet incorporated into DESIGN.md
5. `<project_root>/doc/DATA_MODEL.md` for database structures
6. `<project_root>/doc/API.md` for external APIs
7. `<project_root>/doc/DOCUMENT_RELATIONSHIPS.md` for documentation dependencies
8. Markdown files listed in the "[Dependencies]" section of file headers
9. Read top level HSTC files

Additionally, for business/functional/mock/feature-related tasks ONLY *OR* when in DESIGN mode:
- `<project_root>/doc/PR-FAQ.md` and `/doc/WORKING_BACKWARDS.md` for project vision

For each missing document, explicitly state: "Required document not found: [document path]", compile a complete list of all missing documents, and add this warning: "Implementation based on incomplete documentation. Quality and alignment with project vision may be affected."

Do not access any files in `<project_root>/scratchpad/` directory unless explicitly requested by the user or when creating implementation plans.
Exclude MARKDOWN_CHANGELOG.md files from initial reading to conserve context window space. Only read these changelog files when their content is specifically relevant to the task.

## Implementation Process
For simple changes (single-file modification, bug fix, <50 lines changed):
- Implement changes directly if already in ACT mode. If in another mode, explicitly request the user to switch to ACT mode before proceeding.

For complex changes:
1. *Think deeply about your plan* and **interact with user** to remove ambiguities by asking questions/proposing choices between alternatives 

2. Create a directory using the specific pattern: `<project_root>/scratchpad/<implementation_plan_name_in_lower_snake_case>/`
   
3. Create an overview implementation document at: `<project_root>/scratchpad/<implementation_plan_name_in_lower_snake_case>/plan_overview.md` containing:
   - A MANDATORY documentation section with comprehensive list of ALL documentation files read, including direct file links
   - This exact warning text: "⚠️ CRITICAL: CODING ASSISTANT MUST READ THESE DOCUMENTATION FILES COMPLETELY BEFORE EXECUTING ANY TASKS IN THIS PLAN"
   - Concise explanation of each documentation file's relevance to the implementation
   - Implementation steps organized in sequential logical phases
   - Complete list of all detailed implementation plan file names that will be created
   - Clear reference to the side-car progress file location
   - Essential source documentation excerpts that directly inform the implementation

4. Create a dedicated progress tracking file at: `<project_root>/scratchpad/<implementation_plan_name_in_lower_snake_case>/plan_progress.md` which must track:
   - Current plan creation and implementation status
   - Status indicators using these exact symbols: ❌ Plan not created, 🔄 In progress, ✅ Plan created, 🚧 Implementation in progress, ✨ Completed
   - Consistency check status placeholder (with symbol ❌) 
   - Each specific subtask with its corresponding implementation plan file

5. Create detailed implementation plans following these rules:
   - Name each file according to this pattern: `<project_root>/scratchpad/<implementation_plan_name_in_lower_snake_case>/plan_{subtask_name}.md`
   - Include direct links to all relevant documentation with brief context summaries for each link
   - Create exactly ONE plan chapter at a time before moving to the next
   - Break large plans into multiple steps to prevent context window truncation
   - Update the progress file immediately before starting work on each new plan file
   - Halt plan creation gracefully when context window token usage reaches 80% capacity

6. Perform a comprehensive consistency: Ask the user to do it from a new, clean session:
   - Review all generated plan files against their associated source documentation
   - Mark the progress file with symbol ✨ to confirm completion

7. Implement the plan: Ask user to start from a new, clean session and do following tasks:
   - Review the progress file to determine current implementation status
   - Follow implementation tasks sequentially in the exact order specified in the overview file
   - Update the progress file immediately after completing each task
   - Document any implementation failures with specific error details
   - Halt plan creation gracefully when context window token usage reaches 80% capacity and propose to restart implementation in a fresh session
