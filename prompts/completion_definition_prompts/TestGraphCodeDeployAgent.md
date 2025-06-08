```properties
Version=0.0.1
AgentName=TestGraphCodeDeployAgent
PromptType=Completion Definition
```

## TestGraphCodeDeployAgent Completion Definition

```prompt_markdown
## TestGraphCodeDeployAgent Completion Definition

The TestGraphCodeDeployAgent is considered **complete** when:

### Primary Completion Criteria

1. **Test_Graph Environment Deployment**: Successfully deployed test_graph environments and services with proper isolation and configuration.

2. **Service Orchestration**: Deployed and validated all test_graph service dependencies, infrastructure components, and networking configurations.

3. **Environment Readiness**: Confirmed test_graph environment is ready for execution with all services healthy and accessible.

### Termination Signals

The agent should terminate if:
- Deployment infrastructure is unavailable or failing
- All requested test_graph environments have been deployed successfully
- Critical deployment dependencies are missing or inaccessible
- User explicitly requests deployment termination

### Success Criteria

- Test_graph environments successfully deployed with proper isolation
- All test_graph services are running and healthy
- Environment connectivity and networking validated
- Deployment artifacts and configurations properly applied
```
