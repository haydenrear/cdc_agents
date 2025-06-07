```properties
Version=0.0.1
AgentName=StateGraphOrchestrator
PromptType=State Graph Orchestrator Agent Completion Prompt
```

# DeepCodeAgent System Instruction

```prompt_markdown
Can you please consider whether the task is completed, considering the previous message from agent {{agent_name}}?
If so can you return the context of the result. If not, can you continue with the task by considering
what is still necessary and delegating to the agent that can help continue/complete the task?
```