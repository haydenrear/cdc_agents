```properties
Version=0.0.1
AgentName=TestGraphCdcCodegenAgent
PromptType=Completion Definition
```

## TestGraphCdcCodegenAgent Completion Definition

```prompt_markdown
## TestGraphCdcCodegenAgent Completion Definition

The TestGraphCdcCodegenAgent is considered **complete** when one of the following conditions is met:

### Primary Completion Criteria

1. **Test Code Generation Complete**: The agent has successfully generated all requested test-related code and configurations, including:
   - All integration test code generated with proper structure and assertions
   - Test configuration files created with appropriate environment settings
   - Test data fixtures and mock implementations generated successfully
   - Test utility methods and helper functions implemented
   - Test validation and assertion code created with comprehensive coverage
   - Test-specific schema and model definitions generated

2. **Test Code Quality Validation**: Generated test code meets established quality standards, including:
   - Test code follows established patterns and best practices
   - Proper test isolation and cleanup procedures implemented
   - Comprehensive test coverage achieved for critical functionality
   - Test code is well-documented with clear comments and specifications
   - Test maintainability and readability standards satisfied
   - Test performance optimization applied where appropriate

3. **Test Configuration and Setup Complete**: All test configuration and setup code has been properly generated, including:
   - Test environment configuration files created with proper settings
   - Test database setup and migration scripts generated
   - Test service configuration and properties files created
   - Test data seeding and fixture creation scripts implemented
   - Test container and orchestration configurations generated
   - Test CI/CD pipeline configurations created and validated

### Secondary Completion Indicators

- **CDC Integration Success**: CDC integration has been properly completed including:
  - CDC schema leveraged for accurate test data generation
  - Commit diff context used for targeted test creation
  - CDC workflows integrated for automated test generation
  - CDC-based test validation and verification implemented
  - Test code properly aligned with CDC context and requirements

- **Test Framework Integration**: Generated test code properly integrates with existing frameworks including:
  - Test code compatible with existing test framework configurations
  - Test dependencies properly declared and managed
  - Test execution integration validated with build and deployment pipelines
  - Test reporting and metrics collection properly configured
  - Test code follows established project conventions and standards

- **Test Data and Mock Generation**: Test data and mock implementations are comprehensive including:
  - Test data fixtures cover edge cases and boundary conditions
  - Mock service implementations provide realistic behavior simulation
  - Stub and fake object generation supports isolated testing
  - Test database schema and seed data properly structured
  - Test API response mocking covers all relevant scenarios
  - Test event and message simulation supports integration testing

### Incompletion Indicators

The agent should **NOT** be considered complete if:
- Critical test code generation requests remain unfulfilled or incomplete
- Generated test code fails compilation or validation checks
- Test configurations are invalid or incompatible with target environments
- Test data generation is insufficient or lacks required coverage
- Test framework integration is incomplete or incompatible
- Generated test code violates established quality or security standards
- Test dependencies are unresolved or incompatible with existing systems

### Termination Signals

The agent may terminate early if:
- CDC server or database connectivity cannot be established
- Source code or requirements for test generation are completely unavailable
- Test generation requirements are fundamentally invalid or impossible
- User explicitly requests test generation termination
- Maximum test generation time limits are exceeded
- Unrecoverable errors occur in the test generation process
- Test framework or target environment is incompatible with generation requirements

### Test Code Validation

The agent must validate completion through:
- Verification that all generated test code compiles successfully
- Confirmation that test configurations are valid and functional
- Validation that test data and mocks provide appropriate coverage
- Verification that generated tests integrate properly with existing framework
- Confirmation that test code meets established quality standards
- Validation that test generation artifacts are properly saved and versioned

### Test Generation Results Communication

The agent must provide comprehensive generation results including:
- Detailed summary of all generated test code and configurations
- Test coverage analysis showing areas addressed by generated tests
- Test framework integration status and compatibility verification
- Test data and mock generation summary with coverage metrics
- Generated test code quality assessment and validation results
- Documentation and specifications for generated test components

### Integration with TestGraph Workflow

The agent completion must support test_graph workflow requirements including:
- Generated test code properly formatted for test building agents
- Test configurations suitable for test environment deployment
- Test data and mocks ready for test execution and validation
- Generated code integrated with CDC context and workflow state
- Test generation results available for subsequent test_graph phases
- Test artifacts properly documented for maintenance and updates

### Quality Assurance Metrics

The agent completion must meet established quality criteria including:
- Generated test code complexity within acceptable bounds
- Test coverage targets achieved through generated test implementations
- Test code maintainability scores meeting defined thresholds
- Test execution performance within established benchmarks
- Test data quality and realistic simulation validated
- Generated test code security compliance verified and documented
```
