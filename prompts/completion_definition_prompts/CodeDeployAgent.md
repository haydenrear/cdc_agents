## CodeDeployAgent Completion Definition

```prompt_markdown
## CodeDeployAgent Completion Definition

The CodeDeployAgent is considered **complete** when one of the following conditions is met:

### Primary Completion Criteria

1. **Deployment Execution Complete**: The agent has successfully executed all requested deployments for pre-registered services, including:
   - All deployment processes completed for registered service artifacts
   - Services deployed to target environments successfully
   - Deployment status (success/failure) determined for all services
   - Post-deployment validation and health checks completed

2. **Pre-Registered Service Deployment Validation**: All pre-registered services have been properly deployed, including:
   - Service artifacts deployed to correct target environments
   - Deployment configurations aligned with registered service specifications
   - Inter-service deployment dependencies properly managed
   - Service endpoints accessible and responding correctly

3. **Deployment Results Reporting**: Comprehensive deployment results have been generated and reported, including:
   - Detailed deployment execution summaries for each service
   - Failed deployment diagnostics with root cause analysis
   - Service health status and endpoint verification results
   - Rollback procedures executed if necessary

### Secondary Completion Indicators

- **Service Registry Integration**: The agent has successfully interfaced with the pre-registered service registry including:
  - Service deployment configurations properly retrieved
  - Target environment mappings identified from service metadata
  - Deployment dependencies resolved from service relationships
  - Deployment order determined based on service dependency graph

- **Quality Thresholds Met**: Deployment execution meets established quality standards including:
  - All critical services deployed successfully
  - Service health checks passing in target environments
  - Deployment performance within acceptable time limits
  - No blocking or high-severity deployment failures

- **Environment Management**: Deployment targets have been properly managed including:
  - Target environments prepared and validated
  - Service configurations applied correctly
  - Network connectivity and security policies verified
  - Resource allocation and scaling parameters set appropriately

### Incompletion Indicators

The agent should **NOT** be considered complete if:
- Critical deployments are failing for pre-registered services
- Service registry cannot be accessed or deployment configurations are incomplete
- Deployment execution is incomplete due to environment issues
- Required services are not accessible or responding after deployment
- Deployment results indicate service incompatibilities or critical failures
- Inter-service deployment dependencies cannot be resolved
- Rollback procedures are required but have not been executed

### Termination Signals

The agent may terminate early if:
- Pre-registered service artifacts are completely unavailable
- Service registry is inaccessible or contains invalid deployment configurations
- Target deployment environments are unavailable or inaccessible
- User explicitly requests deployment termination
- Maximum deployment execution time limits are exceeded
- Unrecoverable errors occur in the deployment process
```
