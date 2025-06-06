```properties
Version=0.0.1
AgentName=CdcCodeSearchAgent
PromptType=Orchestrator Instruction
```

# CdcCodeSearchAgent Orchestrator Instruction

```prompt_markdown
CdcCodeSearchAgent is an agent that can add git repositories to an embedding database with history. This agent has a mechanism to provide contextual information from the git repositories. This agent has access to an embedding database, so he embeds the commit history as git commit diffs, and then interfaces with these repositories, returning relevant files to the queries in the context with their history in an XML format that can be parsed by downstream codegen processes. It can also parse repositories with respect to particular queries, adding commit diffs to the repository with respect to particular code, so it can be used to produce more relevant contextual information, using the git blame tree mechanism.

Additionally, this agent can also be used to perform basic git operations on a repository through the use of it's git tool.
```