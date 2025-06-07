## HumanDelegateAgent Completion Definition

```prompt_markdown
## HumanDelegateAgent Completion Definition

The HumanDelegateAgent is considered **complete** when one of the following conditions is met:

### Primary Completion Criteria

1. **Human Input Received**: The agent has successfully obtained required human input or decision-making, including:
   - Clear responses to delegated questions or requests
   - Human approval or rejection of proposed actions
   - Manual intervention completed for complex tasks
   - Required human expertise or judgment provided

2. **Delegation Task Resolved**: The specific task that required human intervention has been addressed, including:
   - Technical decisions made by human operator
   - Manual processes completed successfully
   - Quality assurance or validation performed by human
   - Complex problem-solving guidance provided

3. **Communication Cycle Complete**: The delegation workflow has been fully executed, including:
   - Request properly communicated to human operator
   - Human response received and validated
   - Results properly formatted and returned to calling system
   - Any follow-up clarifications resolved

### Secondary Completion Indicators

- **Data Persistence Success**: Human delegate data has been properly saved and managed including:
  - Interaction logs stored in the base directory
  - Human responses captured accurately
  - Delegation context preserved for future reference
  - Audit trail maintained for compliance

- **Integration Effectiveness**: The agent has successfully bridged automated and human processes without workflow disruption.

### Incompletion Indicators

The agent should **NOT** be considered complete if:
- Human response is still pending or incomplete
- Delegated task remains unresolved or unclear
- Communication with human operator has failed
- Required human expertise has not been obtained
- Data persistence operations have failed
- The calling system is still waiting for delegation results

### Termination Signals

The agent may terminate early if:
- Human operator is unavailable for extended period
- Delegation request cannot be properly communicated
- Base directory for human delegate data is inaccessible
- User explicitly cancels the delegation request
- Maximum wait time for human response is exceeded
- Unrecoverable errors occur in the delegation process
```
