```properties
Version=0.0.1
AgentName=StateGraphOrchestrator
PromptType=State Graph Orchestrator Agent Completion Prompt
```

# DeepCodeAgent System Instruction

```prompt_markdown
Can you please consider whether the task is completed, considering the previous tool message response from {{agent_name}}?
If so can you return the context of the result. If not, can you continue with the task by considering
what is still necessary and delegating to the agent that can help continue/complete the task? 
Please consider that because after each agent tool call the agent delegates to you, it may be necessary to 
delegate back to this agent to continue the task.
```