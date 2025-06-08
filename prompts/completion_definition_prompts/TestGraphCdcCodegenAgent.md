```properties
Version=0.0.1
AgentName=TestGraphCdcCodegenAgent
PromptType=Completion Definition
```

## TestGraphCdcCodegenAgent Completion Definition

```prompt_markdown
## TestGraphCdcCodegenAgent Completion Definition

The TestGraphCdcCodegenAgent is considered **complete** when:

### Primary Completion Criteria

1. **Test_Graph Code Generation**: Successfully generated test_graph code using CDC tools including postgres database queries for repository context and commit analysis.

2. **Generated Code Validation**: Created and validated test implementations, configurations, mock data, and utility functions needed for test_graph execution.

3. **CDC Integration**: Used postgres tool to retrieve repository information and generate contextually appropriate test code based on commit diff analysis.

### Termination Signals

The agent should terminate if:
- Database connectivity to postgres CDC server is lost
- All requested test_graph code generation has been completed
- Code generation tools are unavailable or malfunctioning
- User explicitly requests generation termination

### Success Criteria

- Test_graph code successfully generated with proper test structure
- Generated code includes necessary test data fixtures and mocks
- Code generation based on relevant repository context from CDC database
- Generated artifacts ready for test_graph build and execution
```
