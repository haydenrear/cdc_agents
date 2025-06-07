## CodeBuildAgent Completion Definition

```prompt_markdown
## CodeBuildAgent Completion Definition

The CodeBuildAgent is considered **complete** when one of the following conditions is met:

### Primary Completion Criteria

1. **Build Execution Complete**: The agent has successfully executed all requested builds for pre-registered services, including:
   - All build processes completed for registered service repositories
   - Build artifacts generated and validated for each service
   - Build status (success/failure) determined for all services
   - Build dependencies resolved and satisfied

2. **Pre-Registered Service Build Validation**: All pre-registered services have been properly built, including:
   - Service source code compilation completed successfully
   - Build configurations aligned with registered service specifications
   - Inter-service build dependencies properly resolved
   - Build artifacts meet quality and security standards

3. **Build Results Reporting**: Comprehensive build results have been generated and reported, including:
   - Detailed build execution summaries for each service
   - Failed build diagnostics with root cause analysis
   - Build artifact inventory and verification status
   - Build performance metrics and optimization recommendations

### Secondary Completion Indicators

- **Service Registry Integration**: The agent has successfully interfaced with the pre-registered service registry including:
  - Service source code locations properly identified
  - Build configurations retrieved from service metadata
  - Build dependencies mapped from service relationships
  - Build order determined based on service dependency graph

- **Quality Thresholds Met**: Build execution meets established quality standards including:
  - All critical services build successfully
  - Build artifacts pass security and quality scans
  - Build performance within acceptable time limits
  - No blocking or high-severity build failures

- **Artifact Management**: Build outputs have been properly managed including:
  - Build artifacts stored in appropriate repositories
  - Version tagging and labeling completed
  - Artifact dependencies properly documented
  - Build reproducibility validated

### Incompletion Indicators

The agent should **NOT** be considered complete if:
- Critical builds are failing for pre-registered services
- Service registry cannot be accessed or service definitions are incomplete
- Build execution is incomplete due to missing dependencies
- Required build artifacts are missing or corrupted
- Build results indicate service incompatibilities or critical failures
- Inter-service build dependencies cannot be resolved

### Termination Signals

The agent may terminate early if:
- Pre-registered service source code is completely unavailable
- Service registry is inaccessible or contains invalid build configurations
- Build infrastructure is unavailable or malfunctioning
- User explicitly requests build termination
- Maximum build execution time limits are exceeded
- Unrecoverable errors occur in the build process
```
