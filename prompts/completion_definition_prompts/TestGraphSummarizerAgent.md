```properties
Version=0.0.1
AgentName=TestGraphSummarizerAgent
PromptType=Completion Definition
```

## TestGraphSummarizerAgent Completion Definition

```prompt_markdown
## TestGraphSummarizerAgent Completion Definition

The TestGraphSummarizerAgent is considered **complete** when:

### Primary Completion Criteria

1. **Test_Graph Results Summarization**: Successfully collected and summarized test_graph execution results, metrics, and outcomes using memory tool for information storage and retrieval.

2. **Comprehensive Reporting**: Generated consolidated reports covering test_graph execution status, performance metrics, failure analysis, and trend information.

3. **Knowledge Retention**: Stored test_graph execution context and insights in memory for future reference and continuous improvement analysis.

### Termination Signals

The agent should terminate if:
- Memory storage tools are unavailable or failing
- All requested test_graph summarization has been completed
- No additional test_graph data is available for processing
- User explicitly requests summarization termination

### Success Criteria

- Test_graph execution results comprehensively summarized and documented
- Key metrics, trends, and insights properly identified and reported
- Actionable recommendations generated based on test_graph analysis
- Summary information stored in memory for future test_graph workflow reference
```
