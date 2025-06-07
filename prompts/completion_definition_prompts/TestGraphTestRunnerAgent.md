```properties
Version=0.0.1
AgentName=TestGraphTestRunnerAgent
PromptType=Completion Definition
```

## TestGraphTestRunnerAgent Completion Definition

```prompt_markdown
## TestGraphTestRunnerAgent Completion Definition

The TestGraphTestRunnerAgent is considered **complete** when one of the following conditions is met:

### Primary Completion Criteria

1. **Test Execution Complete**: The agent has successfully executed all requested test suites and scenarios, including:
   - All integration test suites executed with comprehensive result collection
   - Test environment validation completed with health and readiness verification
   - Test performance monitoring completed with benchmark comparison
   - Test result analysis completed with pass/fail categorization and metrics
   - Test failure diagnosis completed with root cause identification
   - Test execution optimization applied for efficiency and resource utilization

2. **Test Environment Validation Complete**: All test environment validation has been successfully performed, including:
   - Test service health and readiness checks passed successfully
   - Test database connectivity and schema validation completed
   - Test infrastructure performance and capacity verified within acceptable limits
   - Test network connectivity and security validation passed
   - Test configuration and environment variable verification completed
   - Test dependency availability and version compatibility confirmed

3. **Test Result Processing Complete**: Comprehensive test result processing has been finished, including:
   - Test execution results collected and properly aggregated
   - Test coverage analysis completed with gap identification
   - Test performance metrics calculated with trend analysis
   - Test failure root cause analysis completed with categorization
   - Test quality metrics generated with improvement recommendations
   - Test execution timeline and resource usage analysis documented

### Secondary Completion Indicators

- **Test Performance Validation**: Test performance monitoring has been successful including:
  - Test execution time tracking completed with optimization recommendations
  - Test resource utilization monitored with efficiency analysis
  - Test throughput and latency measured within acceptable bounds
  - Test bottleneck identification completed with resolution guidance
  - Test scalability assessment completed with capacity planning insights
  - Test performance regression detection completed with alerting

- **CDC Integration Success**: CDC integration has been properly completed including:
  - CDC context leveraged for targeted test execution and validation
  - Commit diff analysis used for test impact assessment and prioritization
  - CDC workflows integrated for automated test validation and reporting
  - CDC-based test result correlation and analysis completed successfully
  - Test execution results properly formatted for CDC workflow consumption

- **Test Quality Assurance**: Test execution meets established quality standards including:
  - Test execution success rates above defined minimum thresholds
  - Test environment consistency and repeatability demonstrated
  - Test data validation and integrity checks passed successfully
  - Test execution anomaly detection completed with proper handling
  - Test results validated against expected outcomes and acceptance criteria
  - Test execution audit trails maintained for compliance and review

### Incompletion Indicators

The agent should **NOT** be considered complete if:
- Critical test suites have failed to execute or are producing inconsistent results
- Test environment validation is incomplete or showing instability
- Required test performance benchmarks are not being met
- Test result analysis is incomplete or missing critical failure information
- Test execution is experiencing unresolved resource or infrastructure issues
- Test coverage is insufficient for critical system components and workflows
- Test execution results are not properly documented or accessible

### Termination Signals

The agent may terminate early if:
- Test environment is completely unavailable or in an unrecoverable state
- Critical test dependencies are missing and cannot be resolved
- Test execution infrastructure is unavailable or malfunctioning
- User explicitly requests test execution termination
- Maximum test execution time limits are exceeded with no progress
- Unrecoverable errors occur that prevent further test execution
- Test requirements or acceptance criteria are fundamentally invalid

### Test Execution Results Validation

The agent must validate completion through:
- Verification that all requested test suites have been executed successfully
- Confirmation that test results are comprehensive and accurately documented
- Validation that test performance metrics meet established benchmarks
- Verification that test environment stability is maintained throughout execution
- Confirmation that test failure analysis provides actionable insights
- Validation that test execution artifacts are properly preserved and accessible

### Test Results Communication

The agent must provide comprehensive test execution results including:
- Detailed test execution summary with comprehensive pass/fail statistics
- Test environment validation report with configuration and performance metrics
- Test performance analysis with benchmark comparisons and optimization recommendations
- Test failure analysis with root cause identification and remediation guidance
- Test coverage report with gap analysis and improvement suggestions
- Test execution timeline with resource utilization and efficiency metrics

### Integration with TestGraph Workflow

The agent completion must support test_graph workflow requirements including:
- Test execution results properly formatted for orchestrator consumption
- Test validation outcomes suitable for workflow decision-making
- Test performance data available for environment optimization
- Test failure information structured for remediation workflow triggers
- Test coverage metrics accessible for quality gate validation
- Test execution context maintained for subsequent workflow phases

### Performance and Quality Metrics

The agent completion must meet established performance criteria including:
- Test execution time within acceptable performance bounds for the test suite size
- Test resource utilization efficiency meeting established optimization targets
- Test reliability demonstrated through consistent and repeatable results
- Test environment stability maintained throughout the complete execution cycle
- Test result accuracy validated through cross-reference and verification procedures
- Test execution scalability verified through load and stress testing scenarios
```
