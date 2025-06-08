```properties
Version=0.0.1
AgentName=TestGraphLibraryEnumerationAgent
PromptType=Completion Definition
```

## TestGraphLibraryEnumerationAgent Completion Definition

```prompt_markdown
## TestGraphLibraryEnumerationAgent Completion Definition

The TestGraphLibraryEnumerationAgent is considered **complete** when:

### Primary Completion Criteria

1. **Test_Graph Library Discovery**: Successfully searched GitHub repositories using search_github_for_sources tool to identify test libraries and frameworks compatible with test_graph requirements.

2. **Dependency Analysis**: Catalogued and analyzed test_graph dependencies, versions, and compatibility matrices for identified libraries and frameworks.

3. **Library Recommendations**: Provided structured recommendations for test libraries, frameworks, and tooling suitable for test_graph integration and execution.

### Termination Signals

The agent should terminate if:
- GitHub search tools are unavailable or API access is denied
- All requested test_graph library enumeration has been completed
- Search quotas are exceeded or connectivity is lost
- User explicitly requests enumeration termination

### Success Criteria

- Test_graph compatible libraries successfully identified and catalogued
- Dependency relationships and version compatibility assessed
- Library recommendations formatted with rationale and implementation guidance
- Search results structured for use by test_graph build and development agents
```
