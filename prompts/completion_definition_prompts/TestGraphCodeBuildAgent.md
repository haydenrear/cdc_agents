```properties
Version=0.0.1
AgentName=TestGraphCodeBuildAgent
PromptType=Completion Definition
```

## TestGraphCodeBuildAgent Completion Definition

```prompt_markdown
## TestGraphCodeBuildAgent Completion Definition

The TestGraphCodeBuildAgent is considered **complete** when:

### Primary Completion Criteria

1. **Test_Graph Build Execution**: Successfully executed test_graph build using the build_code tool with appropriate build configurations for test infrastructure.

2. **Build Artifacts Generated**: Created and validated test_graph build artifacts including compiled code, dependencies, and containerized environments ready for deployment.

3. **Build Validation**: Confirmed build integrity, resolved dependencies, and verified that generated artifacts meet test_graph execution requirements.

### Termination Signals

The agent should terminate if:
- Build infrastructure is unavailable or experiencing persistent failures
- All requested test_graph builds have been completed successfully
- Build dependencies cannot be resolved or are missing
- User explicitly requests build termination

### Success Criteria

- Test_graph code compiled successfully with all dependencies resolved
- Build artifacts packaged and ready for test_graph deployment
- Build process completed within acceptable time limits
- Build validation confirms artifacts are deployment-ready
```
