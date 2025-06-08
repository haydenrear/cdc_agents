```properties
Version=0.0.1
AgentName=TestGraphHumanDelegateAgent
PromptType=Completion Definition
```

## TestGraphHumanDelegateAgent Completion Definition

```prompt_markdown
## TestGraphHumanDelegateAgent Completion Definition

The TestGraphHumanDelegateAgent is considered **complete** when:

### Primary Completion Criteria

1. **Human Session Management**: Successfully initialized session, communicated with human delegates using message_human_delegate tool, and received necessary approvals or feedback.

2. **Validation Completed**: Obtained human validation of test_graph execution results, requirement clarifications, or strategy approvals as requested.

3. **Session Finalization**: Properly finalized the human delegate session and captured all decisions and feedback for test_graph workflow continuation.

### Termination Signals

The agent should terminate if:
- Human delegate session tools are unavailable
- All required human validations and approvals have been obtained
- Human delegate is unavailable or unresponsive for extended period
- User explicitly requests delegation termination

### Success Criteria

- Human delegate session successfully established and managed
- Required test_graph validations, approvals, or clarifications obtained
- Human feedback properly captured and formatted for orchestrator use
- Session cleanly finalized with all decisions documented
```
