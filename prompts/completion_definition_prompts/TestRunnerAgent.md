## TestRunnerAgent Completion Definition

```prompt_markdown
## TestRunnerAgent Completion Definition

The TestRunnerAgent is considered **complete** when one of the following conditions is met:

### Primary Completion Criteria

1. **Test Execution Complete**: The agent has successfully executed all requested tests on pre-registered services, including:
   - All test suites run against registered service endpoints
   - Test results collected and analyzed for each service
   - Pass/fail status determined for all test scenarios
   - Test coverage metrics gathered where applicable

2. **Pre-Registered Service Validation**: All pre-registered services have been properly tested, including:
   - Service availability and health checks completed
   - Functional tests executed against known service interfaces
   - Integration tests run between registered service dependencies
   - Performance benchmarks completed where specified

3. **Test Results Reporting**: Comprehensive test results have been generated and reported, including:
   - Detailed test execution summaries for each service
   - Failed test diagnostics with root cause analysis
   - Test coverage reports and quality metrics
   - Recommendations for service improvements or fixes

### Secondary Completion Indicators

- **Service Registry Integration**: The agent has successfully interfaced with the pre-registered service registry including:
  - Service discovery and endpoint resolution completed
  - Service metadata and configuration properly retrieved
  - Test configurations aligned with registered service specifications
  - Service dependencies properly identified and tested

- **Quality Thresholds Met**: Test execution meets established quality standards including:
  - Minimum test coverage percentages achieved
  - All critical path tests passing
  - Performance benchmarks within acceptable ranges
  - No blocking or high-severity test failures

### Incompletion Indicators

The agent should **NOT** be considered complete if:
- Critical tests are failing on pre-registered services
- Service registry cannot be accessed or services are unavailable
- Test execution is incomplete due to service connectivity issues
- Required test coverage thresholds are not met
- Test results indicate service degradation or critical failures
- Integration tests between registered services are failing

### Termination Signals

The agent may terminate early if:
- Pre-registered services are completely unavailable or unreachable
- Service registry is inaccessible or corrupted
- Test infrastructure is unavailable or malfunctioning
- User explicitly requests test termination
- Maximum test execution time limits are exceeded
- Unrecoverable errors occur in the testing process
```
