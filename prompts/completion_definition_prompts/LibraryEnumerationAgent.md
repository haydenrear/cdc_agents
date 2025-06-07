## LibraryEnumerationAgent Completion Definition

```prompt_markdown
## LibraryEnumerationAgent Completion Definition

The LibraryEnumerationAgent is considered **complete** when one of the following conditions is met:

### Primary Completion Criteria

1. **Library Enumeration Complete**: The agent has successfully identified and catalogued all relevant libraries, dependencies, or packages within the target scope, including:
   - Complete list of discovered libraries with versions
   - Repository URLs and source locations identified
   - Dependency relationships mapped accurately
   - License and metadata information collected

2. **GitHub Integration Success**: When using GitHub tools, the agent has:
   - Successfully queried GitHub repositories for library information
   - Retrieved accurate repository URLs and metadata
   - Identified relevant packages and their relationships
   - Collected comprehensive library ecosystem data

3. **Enumeration Scope Satisfied**: All requested enumeration criteria have been met, including:
   - Target programming languages covered
   - Specified dependency trees fully traversed
   - Required library categories identified
   - Requested depth of enumeration achieved

### Secondary Completion Indicators

- **Data Quality Standards Met**: Enumerated library information meets quality requirements including:
  - Accurate version numbers and release information
  - Valid repository URLs and source links
  - Consistent naming and classification
  - Complete dependency relationship mapping

- **GitHub Tool Effectiveness**: GitHub integration has provided valuable results without authentication or rate limit issues.

### Incompletion Indicators

The agent should **NOT** be considered complete if:
- Library enumeration is incomplete or missing critical dependencies
- GitHub API calls fail due to authentication or rate limiting issues
- Repository URLs are invalid or inaccessible
- Dependency relationships are incorrectly mapped
- User indicates additional libraries or scope expansion is needed
- Critical library metadata is missing or inaccurate

### Termination Signals

The agent may terminate early if:
- GitHub API access is unavailable or blocked
- Target repositories or libraries do not exist
- Authentication credentials are invalid or expired
- User explicitly requests termination
- Maximum enumeration depth or time limits are reached
- Unrecoverable errors occur in library discovery process
```
