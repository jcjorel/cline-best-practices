# MANDATORY CODE DOCUMENTATION PATTERNS

⚠️ CRITICAL: ALL functions, methods, and classes MUST include the three-section documentation pattern regardless of size or complexity. NO EXCEPTIONS PERMITTED (except for Markdown files). This is a non-negotiable project standard that takes precedence over all other considerations except correct code functionality.

## Documentation Pattern Reminder:
```
[Function/Class method/Class intent] <!-- It is **critical** to fully capture and contextualize the intent -->
[Design principles]
[Implementation details]
```

## Function/Method/Class Documentation Verification Checklist
After implementing ANY function, method, or class, ALWAYS perform this verification:
1. Check: Does documentation include ALL THREE required sections: "[Function/Class method/Class intent]", "[Implementation details]", and "[Design principles]"?
2. Check: Are these three sections in the EXACT order specified?
3. Check: Is the documentation format consistent with the language-specific example in GENAI_FUNCTION_TEMPLATE.txt?
4. If ANY check fails, STOP and FIX before proceeding further

## Self-Correction Mechanism
If you notice you've implemented code without proper documentation:
1. IMMEDIATELY stop further implementation
2. Add the missing documentation sections in the correct order
3. Verify against the checklist
4. Resume implementation only after documentation is complete

## Code Documentation Standard

All code must be documented at TWO distinct levels without exception:

### File-level Documentation
- ALWAYS use the template from `GENAI_HEADER_TEMPLATE.txt` without modification
- Apply this header to ALL non-markdown files in the project
- Place the header at the very top of each file before any other content
   
**Example File-level Header (in Python)**:
```python
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
# <Describe the detailed purpose of this file. Intent must be fully captured and contextualized. >
###############################################################################
# [Source file design principles]
# <List key design principles guiding this implementation>
###############################################################################
# [Source file constraints]
# <Document any limitations or requirements for this file>
###############################################################################
# [Dependencies] <!-- Never reference documents in <project_root>/scratchpad/ directory -->
# <File paths of others codebase and documentation files. List also language specific libraries if any>
# <List of markdown files in doc/ that provide broader context for this file>
# <Prefix the dependency with its kind like "<codebase|system|other>:<dependency>"
#    <"codebase" kind means a reference to any artifact in the current project codebase>
#    <"system" kind means a reference toward an external artifact provided by the environement (files, librairies, modules...)>
###############################################################################
# [GenAI tool change history] <!-- Change history sorted from the newest to the oldest -->
# YYYY-MM-DDThh:mm:ssZ : <summary of change> by CodeAssistant
# * <change detail>
###############################################################################
```

### Function/Class-level Documentation
- This documentation is MANDATORY for ALL functions, methods, and classes without exception
- Documentation MUST include these specific labeled sections in this exact order:
  a. "[Function/Class method/Class intent]" - Purpose and role description
  b. "[Design principles]" - Patterns and approaches used
  c. "[Implementation details]" - Key technical implementation notes
- Include standard language-appropriate parameter/return documentation according to language conventions
- ALWAYS follow the exact template provided in `GENAI_FUNCTION_TEMPLATE.txt`
- These sections are required for all functions and class methods regardless of complexity or size

#### Documentation Quality Standards
- Write insightful comments that allow developers to understand key aspects of file and class/methods/functions without reading code
- When using adjectives (like "clear", "simple", "efficient", "appropriate", "optimal", "robust", etc.), ALWAYS provide one or more specific justifications in the same sentence to prove the adjective is deserved
- Avoid vague wording in justifications and provide precise technical reasons
- "Design principles" section should hold meaningful information to use the file and its content elsewhere in the codebase (architectural patterns, limitations if any)
- "Implementation details" section should contain information needed to understand and maintain the file content itself

**Python Function Documentation Example**:
```python
def authenticate_user(credentials, options=None):
    """
    [Function intent]
    Authenticates a user against the system using provided credentials.
    
    [Design principles]
    Follows zero-trust architecture principles with complete validation.
    Uses stateless authentication with short-lived tokens.
    
    [Implementation details]
    Uses bcrypt for password verification and JWT for token generation.
    Applies rate limiting based on username to prevent brute force attacks.
    
    Args:
        credentials (dict): User login credentials
            - username (str): User's unique identifier
            - password (str): User's plaintext password
        options (dict, optional): Optional authentication parameters
            - remember_me (bool): Whether to extend token validity
            
    Returns:
        dict: Object containing JWT token and user profile
        
    Raises:
        AuthenticationError: When credentials are invalid
        ValidationError: When credentials format is incorrect
    """
    # Implementation...
```

**JavaScript Class Documentation Example**:
```javascript
/**
 * [Class intent]
 * Manages user authentication state and processes throughout the application.
 *
 * [Design principles]
 * Single responsibility for auth state management.
 * Clear separation between auth logic and UI components.
 *
 * [Implementation details]
 * Implements the Observer pattern to notify components of auth state changes.
 * Uses localStorage for persistent login state with encryption.
 *
 * @class AuthManager
 */
class AuthManager {
  /**
   * [Class method intent]
   * Creates a new AuthManager instance with initial configuration.
   *
   * [Design principles]
   * Fail-secure initialization with validation of stored credentials.
   *
   * [Implementation details]
   * Sets up listeners and initializes from encrypted localStorage if available.
   *
   * @param {Object} config - Configuration options
   * @param {boolean} config.autoRefresh - Whether to auto-refresh tokens
   */
  constructor(config) {
    // Implementation...
  }
  
  // Additional methods...
}
```

IMPORTANT: These three documentation sections ("[Function/Class method/Class intent]", "[Design principles]", and "[Implementation details]") must be included for ALL functions, methods and classes regardless of their complexity or size. No exceptions are permitted.
