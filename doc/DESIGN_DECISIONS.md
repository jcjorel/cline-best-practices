# Design Decisions

This document tracks new design decisions that haven't yet been integrated into the core documentation files. Once integrated, decisions are removed from this file and merged into the appropriate core documentation.

## 2025-04-20: Centralized Component Registration with Dependency Injection

### Context
Previously, components defined their dependencies through a `dependencies` property in each component class. Each component was also responsible for manually fetching its dependencies using `context.get_component()` during initialization. This approach scattered essential configuration across many files, making it difficult to understand the dependency graph and increasing the chance of errors.

### Decision
Implement a centralized component registration mechanism that allows registering components and declaring dependencies in one place, combined with direct dependency injection during initialization.

### Rationale
- **Centralized Configuration**: Having all component dependencies declared in one place makes the system architecture more visible and easier to understand.
- **Reduced Duplication**: Eliminates the need to declare dependencies in multiple places.
- **Improved Testability**: Direct dependency injection makes components more testable by allowing easy mocking of dependencies.
- **Simplified Component Implementation**: Components receive their dependencies directly without having to fetch them.

### Implementation
1. Created a `ComponentRegistry` class for centralized component registration
2. Enhanced the `Component` base class to accept dependencies during initialization
3. Updated the `ComponentSystem` to resolve and inject dependencies
4. Modified component implementations to use the injected dependencies
5. Removed the deprecated `dependencies` property from the Component base class

### Implications
- All component implementations needed to be updated to accept and use injected dependencies
- The system now has a clearer separation between component registration and implementation
- Testing is simplified due to easier dependency mocking
- New components will be easier to integrate with explicit dependency declaration

### Alternatives Considered
- **Service Locator Pattern**: Continue with the existing approach where components fetch dependencies themselves. Rejected due to reduced visibility and testability.
- **Complex Dependency Injection Framework**: Implementing a full DI container with autowiring, scopes, etc. Rejected as overly complex for our needs.
- **Constructor Injection**: Passing dependencies at component construction time. Rejected due to the need for deeper changes to the component lifecycle.

### Related Components
- `ComponentSystem`
- `Component` base class
- `ComponentRegistry`
- All concrete component implementations
