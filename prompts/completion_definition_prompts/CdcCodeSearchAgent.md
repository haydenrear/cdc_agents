## CdcCodeSearchAgent Completion Definition

```prompt_markdown
## CdcCodeSearchAgent Completion Definition

The CdcCodeSearchAgent is considered **complete** when one of the following conditions is met:

### Primary Completion Criteria

1. **Search Query Resolved**: The agent has successfully found and returned relevant code snippets, files, or patterns that match the user's search criteria, including:
   - Accurate file paths and line numbers
   - Relevant code context surrounding matches
   - Clear explanation of what was found and its relevance

2. **Comprehensive Search Coverage**: All relevant search strategies have been exhausted, including:
   - Filesystem searches across appropriate directories
   - Git repository searches using version control history
   - Pattern matching and regular expression searches
   - Multi-file searches when appropriate

3. **User Query Satisfaction**: The search results fully address the user's original request and provide actionable information for their use case.

### Secondary Completion Indicators

- **Search Results Quality**: Found results are accurate, relevant, and properly formatted with:
  - Correct file paths and locations
  - Appropriate code context
  - Clear explanations of relevance
  - Properly formatted output

- **Tool Integration Success**: All MCP tools (filesystem, git) have been used effectively without errors and have provided meaningful results.

### Incompletion Indicators

The agent should **NOT** be considered complete if:
- Search queries return no results when results should exist
- Found results are incomplete or lack necessary context
- File system or git tool errors prevent proper searching
- The user indicates the search was insufficient or incorrect
- Additional search refinement is clearly needed

### Termination Signals

The agent may terminate early if:
- No relevant files or code exist for the search criteria
- Search tools are unavailable or malfunctioning
- User explicitly requests termination
- Maximum search depth or time limits are reached
```
