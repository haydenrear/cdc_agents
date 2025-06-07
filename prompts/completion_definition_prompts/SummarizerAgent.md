## SummarizerAgent Completion Definition

```prompt_markdown
## SummarizerAgent Completion Definition

The SummarizerAgent is considered **complete** when one of the following conditions is met:

### Primary Completion Criteria

1. **Summary Generated**: The agent has successfully produced a comprehensive summary that captures the essential information from the input content, including:
   - Key points and main themes identified
   - Important details preserved while reducing verbosity
   - Logical structure and flow maintained
   - Appropriate level of detail for the intended audience

2. **Token Limit Management**: The agent has successfully processed content that exceeded token limits by:
   - Creating coherent summaries that fit within token constraints
   - Preserving critical information while removing redundancy
   - Maintaining context and meaning across summarization passes

3. **Memory Integration**: When using memory tools, the agent has:
   - Successfully stored relevant information for future recall
   - Retrieved and incorporated previously stored context appropriately
   - Maintained continuity across multiple summarization sessions

### Secondary Completion Indicators

- **Quality Thresholds Met**: The generated summary meets quality standards including:
  - Accuracy in representing the original content
  - Clarity and readability of the summarized text
  - Appropriate level of abstraction for the use case
  - Preservation of critical technical details when relevant

- **Memory Tool Success**: Memory operations have completed successfully without errors and provide value for ongoing summarization tasks.

### Incompletion Indicators

The agent should **NOT** be considered complete if:
- Generated summaries are inaccurate or miss critical information
- Token limits are exceeded without proper summarization
- Memory tool operations fail or provide corrupted data
- The summary lacks coherence or logical structure
- User indicates the summary is insufficient or incorrect

### Termination Signals

The agent may terminate early if:
- Input content is empty or invalid
- Memory tool services are unavailable
- Maximum token processing limits are reached
- User explicitly requests termination
- Unrecoverable errors occur in the summarization process
```
