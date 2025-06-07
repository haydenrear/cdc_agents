```properties
Version=0.0.1
AgentName=TestGraphCodeBuildAgent
PromptType=Completion Definition
```

## TestGraphCodeBuildAgent Completion Definition

```prompt_markdown
## TestGraphCodeBuildAgent Completion Definition

The TestGraphCodeBuildAgent is considered **complete** when one of the following conditions is met:

### Primary Completion Criteria

1. **Test Build Execution Complete**: The agent has successfully executed all requested test builds and compilation tasks, including:
   - All test code compiled successfully with proper dependency resolution
   - Test-specific modules and libraries built with optimized configurations
   - Test artifacts packaged and validated for distribution and deployment
   - Test executable artifacts generated with proper metadata and documentation
   - Test dependency integrity validated and security scanned
   - Test build configurations validated against quality and performance standards

2. **Test Environment Build Validation**: All test environment builds have been properly completed, including:
   - Containerized test environments built with proper configuration
   - Test infrastructure and deployment scripts compiled successfully
   - Test environment configuration and setup tools packaged
   - Test database schemas and migration scripts built and validated
   - Test service configurations and startup scripts prepared
   - Test environment validation and health check tools generated

3. **Test Artifact Management Complete**: Test build outputs have been properly managed and validated, including:
   - Test build artifacts stored in appropriate repositories with proper versioning
   - Test package dependencies bundled with accurate version manifests
   - Test configuration packages created with environment-specific settings
   - Test data archives built with proper versioning and metadata
   - Test documentation and specification artifacts packaged
   - Test container images created with optimized configurations and security scanning

### Secondary Completion Indicators

- **Test Build Quality Validation**: Build execution meets established quality standards including:
  - All critical test code compiles successfully without errors
  - Test build artifacts pass security and quality scans
  - Test build performance within acceptable time limits
  - Test dependency conflicts resolved and compatibility validated
  - Test build reproducibility demonstrated and documented
  - Test artifact integrity verified through checksums and validation

- **Test Dependency Resolution Success**: Test dependency management has been successful including:
  - Test-specific dependencies resolved and built successfully
  - Test dependency isolation and version compatibility maintained
  - Test utility libraries and helper modules compiled
  - Test data generation and fixture creation tools built
  - Test framework extensions and custom utilities packaged
  - Test dependency security vulnerabilities addressed and patched

- **Build Process Optimization**: Test build processes have been optimized including:
  - Incremental building implemented for faster test feedback cycles
  - Test dependency caching and reuse strategies optimized
  - Parallel compilation achieved for independent test modules
  - Test artifact packaging and distribution optimized
  - Test resource allocation and memory usage optimized
  - Test environment provisioning and setup time minimized

### Incompletion Indicators

The agent should **NOT** be considered complete if:
- Critical test builds are failing or not executing properly
- Required test artifacts are missing, corrupted, or incomplete
- Test dependency resolution is incomplete or has unresolved conflicts
- Test build configurations are invalid or incompatible with target environments
- Test environment builds are failing or producing unstable environments
- Test build performance is unacceptable or exceeds time limits
- Test artifact security scans indicate critical vulnerabilities

### Termination Signals

The agent may terminate early if:
- Test source code is completely unavailable or inaccessible
- Build infrastructure is unavailable or malfunctioning
- Critical build dependencies are missing and cannot be resolved
- User explicitly requests build termination
- Maximum build execution time limits are exceeded
- Unrecoverable errors occur in the build process
- Build requirements or specifications are fundamentally invalid

### Test Build Results Validation

The agent must validate completion through:
- Verification that all requested test builds completed successfully
- Confirmation that test artifacts meet quality and security standards
- Validation that test dependencies are properly resolved and compatible
- Verification that test environments can be properly provisioned
- Confirmation that test build performance meets established benchmarks
- Validation that test artifacts are properly documented and accessible

### Build Results Communication

The agent must provide comprehensive build results including:
- Detailed test build execution summary with success/failure metrics
- Test artifact inventory with versions, checksums, and metadata
- Test dependency analysis with compatibility and security assessment
- Test build performance metrics with optimization recommendations
- Test environment validation results with readiness indicators
- Build troubleshooting information for any failures or issues

### Integration with TestGraph Workflow

The agent completion must support test_graph workflow requirements including:
- Test artifacts properly prepared for test execution agents
- Test environment builds ready for deployment and validation
- Test build metadata available for test result analysis
- Test dependency information accessible for test environment setup
- Build performance metrics supporting workflow optimization
- Test artifact security validation enabling compliance verification

### Performance and Quality Metrics

The agent completion must meet established performance criteria including:
- Test build execution time within acceptable performance bounds
- Test artifact quality meeting defined minimum standards
- Test dependency resolution efficiency achieving target benchmarks
- Test build resource utilization optimized for cost and performance
- Test environment build reliability demonstrated through validation
- Test build scalability verified through load and stress testing
```
