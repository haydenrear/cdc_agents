```properties
Version=0.0.1
AgentName=TestGraphAgent
PromptType=Completion Definition
```

## TestGraphAgent Completion Definition

```prompt_markdown
## TestGraphAgent Completion Definition

The TestGraphAgent is considered **complete** when one of the following conditions is met:

### Primary Completion Criteria

1. **Test Workflow Execution Complete**: The agent has successfully orchestrated the complete test_graph workflow, including:
   - Test discovery phase completed with comprehensive test artifact identification
   - Test analysis phase completed with coverage and quality assessment
   - Test generation phase completed with necessary test code creation/updates
   - Test building phase completed with successful compilation and packaging
   - Test execution phase completed with comprehensive test run results
   - Test validation phase completed with results analysis and verification

2. **Integration Test Validation Complete**: All integration tests have been properly executed and validated, including:
   - Service integration tests executed successfully with acceptable pass rates
   - API contract tests validated with proper service interactions
   - Database integration tests completed with transaction validation
   - End-to-end workflow tests executed with comprehensive scenario coverage
   - Performance tests completed with acceptable benchmark results
   - Security and compliance tests validated with proper authorization checks

3. **Test Environment Validation**: Test environments have been properly managed and validated, including:
   - Test environment setup and configuration completed successfully
   - Test service deployment and readiness validation completed
   - Test database preparation and data loading completed
   - Test infrastructure health checks passed successfully
   - Test environment cleanup and resource management completed
   - Test environment security and isolation validated

### Secondary Completion Indicators

- **Test Coverage Achievement**: The agent has achieved comprehensive test coverage including:
  - Critical business logic covered by integration tests
  - Service boundaries and contracts properly tested
  - Error handling and edge cases validated through testing
  - Performance benchmarks established and validated
  - Security requirements tested and compliance verified

- **Test Quality Validation**: Test execution meets established quality standards including:
  - Test execution success rates above defined thresholds
  - Test performance within acceptable time limits
  - Test reliability and repeatability demonstrated
  - Test artifacts properly documented and accessible
  - Test results properly analyzed and reported

- **Orchestration Success**: Sub-agent coordination has been successful including:
  - All TestGraphOrchestrated agents completed their assigned tasks
  - Agent communication and data flow functioned properly
  - Resource allocation and scheduling optimized effectively
  - Error handling and recovery mechanisms functioned as expected
  - Workflow state management maintained consistency throughout

### Incompletion Indicators

The agent should **NOT** be considered complete if:
- Critical integration tests are failing or not executing
- Test environment setup or configuration is incomplete or unstable
- Required test artifacts are missing or not properly built
- Test coverage is insufficient for critical system components
- Test execution results indicate system instability or major defects
- TestGraphOrchestrated agents have not completed their required tasks
- Test workflow has encountered unrecoverable errors or blockers

### Termination Signals

The agent may terminate early if:
- Test environment is completely unavailable or unrecoverable
- Critical test dependencies are missing and cannot be resolved
- System under test is in a completely non-functional state
- User explicitly requests test workflow termination
- Maximum test execution time limits are exceeded with no progress
- Unrecoverable errors occur that prevent further test execution
- Test requirements or acceptance criteria are fundamentally invalid

### Test Results Communication

The agent must provide comprehensive results to the parent DeepCodeOrchestrator including:
- Detailed test execution summary with pass/fail metrics
- Test coverage analysis and gap identification
- Test performance benchmarks and comparison results
- Test environment status and resource utilization
- Recommendations for system improvements based on test findings
- Test artifacts and documentation for future reference
```
