```prompt_markdown
## DeepCodeAgent Completion Definition

The DeepCodeAgent is considered **complete** when one of the following conditions is met:

### Primary Completion Criteria

1. **Final Answer Provided**: The agent has produced a comprehensive final answer that addresses the original user query or research question, including:
   - Clear conclusions based on code analysis
   - Actionable recommendations or insights
   - Supporting evidence from the codebase examination

2. **Research Exhaustion**: All relevant code paths, patterns, and architectural components have been thoroughly analyzed, and no additional meaningful insights can be derived from further investigation.

3. **User Satisfaction Confirmed**: The agent has explicitly confirmed with the user that the research objectives have been met and no further analysis is required.

### Secondary Completion Indicators

- **Quality Thresholds Met**: All quality checks have passed, including:
  - Code trajectory validation shows positive progress
  - Refactoring recommendations are sound and implementable
  - Dead code identification is accurate and justified
  - Test validity assessments are thorough and correct
  - Business requirements have been properly addressed

- **Agent Response Refinement Complete**: No further refinement of sub-agent responses is needed, indicating that the orchestrated research has reached satisfactory quality levels.

### Incompletion Indicators

The agent should **NOT** be considered complete if:
- Critical code paths remain unanalyzed
- Quality checks indicate potential issues or collapse in the research trajectory
- Sub-agents are providing responses that require significant refinement
- The user has indicated additional research directions or concerns
- Business requirements are not fully addressed or understood

### Termination Signals

The agent may terminate early if:
- Maximum recursion limits are reached
- User explicitly requests termination
- System resources are exhausted
- Unrecoverable errors occur in the research process
```
