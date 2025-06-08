```properties
Version=0.0.1
AgentName=TestGraphCdcCodeSearchAgent
PromptType=Completion Definition
```

## TestGraphCdcCodeSearchAgent Completion Definition

```prompt_markdown
## TestGraphCdcCodeSearchAgent Completion Definition

The TestGraphCdcCodeSearchAgent is considered **complete** when:

### Primary Completion Criteria

1. **Test_Graph Component Discovery**: Successfully searched and located test_graph related code, configurations, and dependencies using filesystem and git tools.

2. **Repository Analysis**: Used CDC tools to analyze commit diff context and retrieve relevant test_graph code artifacts from the embedded repository.

3. **Search Results Provided**: Delivered structured search results containing test implementations, configurations, dependencies, and coverage information needed for test_graph operations.

### Termination Signals

The agent should terminate if:
- Repository access fails or CDC server connectivity is lost
- Search tools are unavailable or malfunctioning  
- All requested test_graph components have been discovered and analyzed
- User explicitly requests termination

### Success Criteria

- Test_graph components successfully identified and catalogued
- Repository context properly embedded and searchable
- Search results formatted for use by other test_graph agents
- All requested search patterns and dependencies discovered
```
