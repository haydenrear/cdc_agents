```properties
Version=0.0.1
AgentName=TestGraphTestRunnerAgent
PromptType=Completion Definition
```

## TestGraphTestRunnerAgent Completion Definition

```prompt_markdown
## TestGraphTestRunnerAgent Completion Definition

The TestGraphTestRunnerAgent is considered **complete** when:

### Primary Completion Criteria

1. **Test_Graph Execution**: Successfully executed test_graph integration tests using the execute_code tool with appropriate test runner configurations.

2. **Test Results Collected**: Gathered comprehensive test execution results including pass/fail status, execution time, and error details from the test run.

3. **Environment Validation**: Confirmed test_graph environment readiness and validated that all test dependencies are available before execution.

### Termination Signals

The agent should terminate if:
- Test execution infrastructure is unavailable or malfunctioning
- All requested test_graph tests have been executed successfully
- Test environment is completely inaccessible
- User explicitly requests execution termination

### Success Criteria

- Test_graph tests executed with clear pass/fail results
- Test execution metrics and performance data captured
- Test failures properly diagnosed with actionable error information
- Test results formatted for orchestrator decision-making
```
