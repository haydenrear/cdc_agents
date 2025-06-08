```properties
Version=0.0.1
AgentName=TestGraphAgent
PromptType=Completion Definition
```

## TestGraphAgent Completion Definition

```prompt_markdown
## TestGraphAgent Completion Definition

The TestGraphAgent is considered **complete** when:

### Primary Completion Criteria

1. **Test_Graph Workflow Orchestration**: Successfully coordinated all TestGraphOrchestrated agents to complete the full test_graph lifecycle including discovery, build, deployment, execution, and validation.

2. **Agent Coordination Success**: All managed TestGraphOrchestrated agents have completed their assigned tasks with successful handoffs and state management throughout the workflow.

3. **Test_Graph Execution Validated**: Confirmed that test_graph has been successfully executed with results validated and properly summarized for parent orchestrator consumption.

### Termination Signals

The agent should terminate if:
- All TestGraphOrchestrated agents have completed their workflows successfully
- Critical test_graph infrastructure is completely unavailable
- Test_graph workflow has encountered unrecoverable errors across multiple agents
- User explicitly requests test_graph workflow termination

### Success Criteria

- Complete test_graph workflow executed from discovery through validation
- All TestGraphOrchestrated agents successfully coordinated and completed
- Test_graph execution results validated and summarized
- Workflow state properly maintained and handed back to parent DeepCodeOrchestrator
```
