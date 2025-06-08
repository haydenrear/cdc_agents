```properties
Version=0.0.1
AgentName=TestRunnerAgent
PromptType=Completion Definition
```

## TestRunnerAgent Completion Definition

```prompt_markdown
## TestRunnerAgent Completion Definition

The TestRunnerAgent is considered **complete** when:

### Primary Completion Criteria

1. **Test Execution**: Successfully executed tests using the execute_code tool with appropriate test runner configurations for the target services.

2. **Test Results Collected**: Gathered comprehensive test execution results including pass/fail status, execution time, and error details from the test run.

3. **Service Validation**: Confirmed target services are accessible and validated that test execution covers the required functionality and endpoints.

### Termination Signals

The agent should terminate if:
- Test execution infrastructure is unavailable or malfunctioning
- All requested tests have been executed successfully
- Target services are completely inaccessible
- User explicitly requests execution termination

### Success Criteria

- Tests executed with clear pass/fail results
- Test execution metrics and performance data captured
- Test failures properly diagnosed with actionable error information
- Test results formatted for consumption by requesting agents
```
