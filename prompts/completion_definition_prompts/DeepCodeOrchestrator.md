## DeepCodeOrchestrator Completion Definition

```prompt_markdown
## DeepCodeOrchestrator Completion Definition

The DeepCodeOrchestrator is considered **complete** when one of the following conditions is met:

### Primary Completion Criteria

1. **Orchestration Objective Achieved**: The orchestrator has successfully coordinated all sub-agents to achieve the primary research or analysis objective, including:
   - All required DeepCodeAgent instances have completed their assigned tasks
   - Research objectives have been fully addressed through coordinated sub-agent activities
   - Final consolidated results have been generated from sub-agent outputs
   - Quality validation across all orchestrated research has been completed

2. **Sub-Agent Coordination Complete**: All necessary sub-agent interactions have been successfully managed, including:
   - Task distribution to appropriate DeepCodeAgent instances completed
   - Sub-agent responses collected and validated
   - Inter-agent dependencies resolved and coordinated
   - Resource allocation and scheduling optimized across agents

3. **Research Synthesis Delivered**: The orchestrator has produced a comprehensive synthesis of all sub-agent findings, including:
   - Consolidated analysis from multiple code research perspectives
   - Cross-referenced findings and recommendations
   - Unified conclusions that address the original research scope
   - Actionable insights derived from orchestrated research activities

### Secondary Completion Indicators

- **Quality Orchestration Standards Met**: The orchestration process meets established quality requirements including:
  - Sub-agent outputs demonstrate consistent quality levels
  - Research coverage is comprehensive without significant gaps
  - Cross-validation between sub-agents confirms accuracy
  - Orchestration efficiency meets performance benchmarks

- **Resource Management Success**: Orchestration resources have been effectively managed including:
  - Optimal allocation of computational resources across sub-agents
  - Parallel processing utilized where appropriate
  - Memory and processing limits respected across all agents
  - Task scheduling optimized for research objectives

- **Recursion Control Effective**: Orchestration recursion has been properly managed including:
  - Maximum recursion limits respected (configured at 100)
  - Recursive depth appropriate for research complexity
  - No infinite loops or excessive recursive calls
  - Graceful handling of recursive termination conditions

### Incompletion Indicators

The orchestrator should **NOT** be considered complete if:
- Critical sub-agents have failed or produced incomplete results
- Research objectives remain partially addressed or unresolved
- Sub-agent coordination has resulted in conflicts or inconsistencies
- Quality validation indicates significant issues in orchestrated research
- Resource limits have been exceeded without proper resolution
- Recursion limits have been reached without achieving objectives
- Final synthesis is incomplete or lacks necessary depth

### Termination Signals

The orchestrator may terminate early if:
- Maximum recursion limits (100) are reached
- Sub-agent failures prevent achievement of research objectives
- Resource exhaustion prevents continued orchestration
- User explicitly requests orchestration termination
- Unrecoverable errors occur in the orchestration process
- Critical dependencies for sub-agent coordination are unavailable
```
