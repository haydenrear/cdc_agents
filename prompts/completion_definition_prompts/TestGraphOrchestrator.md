```properties
Version=0.0.1
AgentName=TestGraphOrchestrator
PromptType=Completion Definition
```

## TestGraphOrchestrator Completion Definition

```prompt_markdown
## TestGraphOrchestrator Completion Definition

The TestGraphOrchestrator is considered **complete** when one of the following conditions is met:

### Primary Completion Criteria

1. **State Graph Workflow Complete**: The orchestrator has successfully managed the complete test_graph state graph workflow, including:
   - All TestGraphOrchestrated agents have completed their assigned tasks
   - State transitions have occurred properly through all required workflow phases
   - Agent coordination and communication has functioned correctly
   - Workflow state consistency has been maintained throughout execution
   - All inter-agent dependencies have been resolved successfully
   - Final workflow state indicates successful completion

2. **Test Integration Workflow Complete**: All test integration workflows have been properly orchestrated, including:
   - Test discovery workflow completed with comprehensive artifact identification
   - Test code generation workflow completed with quality validation
   - Test building workflow completed with successful compilation and packaging
   - Test execution workflow completed with comprehensive result collection
   - Test validation workflow completed with proper analysis and reporting
   - Test environment management workflow completed with proper setup and cleanup

3. **Agent Orchestration Success**: All TestGraphOrchestrated agents have been successfully coordinated, including:
   - Task delegation to appropriate agents completed successfully
   - Agent progress monitoring and status tracking maintained accurately
   - Resource allocation and scheduling optimized across all agents
   - Error handling and recovery mechanisms functioned properly
   - Agent communication protocols maintained consistency
   - Workflow synchronization points achieved successfully

### Secondary Completion Indicators

- **Sub-Graph Integration**: The orchestrator has successfully integrated as a sub-graph within DeepCodeOrchestrator including:
  - Proper communication with parent DeepCodeOrchestrator maintained
  - Context and state information properly shared and synchronized
  - Results and recommendations properly formatted for parent consumption
  - Sub-graph boundaries and responsibilities clearly maintained
  - Parent orchestrator requirements and expectations fulfilled

- **Workflow Quality Gates**: All established quality gates have been met including:
  - Test coverage thresholds achieved across all tested components
  - Test execution success rates above defined minimum standards
  - Test performance benchmarks met within acceptable ranges
  - Test environment stability and reliability validated
  - Test artifact quality and completeness verified
  - Test documentation and reporting standards satisfied

- **Resource Management Success**: Test workflow resources have been properly managed including:
  - Test environment provisioning and scaling completed successfully
  - Test execution resource allocation optimized effectively
  - Test data and artifact storage managed properly
  - Test infrastructure utilization optimized for cost and performance
  - Test workflow cleanup and resource deallocation completed
  - Resource monitoring and alerting functioned correctly

### Incompletion Indicators

The orchestrator should **NOT** be considered complete if:
- Any TestGraphOrchestrated agents have not completed their required tasks
- Critical workflow states have not been achieved or validated
- Test integration workflows are incomplete or have failed
- State graph transitions are blocked or have encountered unrecoverable errors
- Required test artifacts or results are missing or invalid
- Communication with parent DeepCodeOrchestrator is incomplete or failed
- Workflow synchronization points have not been properly achieved

### Termination Signals

The orchestrator may terminate early if:
- Parent DeepCodeOrchestrator explicitly requests workflow termination
- Critical TestGraphOrchestrated agents are unavailable or unrecoverable
- Test environment infrastructure is completely unavailable
- Maximum workflow execution time limits are exceeded
- Unrecoverable errors occur in the state graph workflow
- Test requirements or acceptance criteria are fundamentally invalid
- Resource constraints prevent further workflow execution

### State Graph Completion Validation

The orchestrator must validate completion through:
- Verification that all required state transitions have occurred
- Confirmation that all TestGraphOrchestrated agents report completion
- Validation that workflow outputs meet established quality criteria
- Verification that all error conditions have been properly handled
- Confirmation that all cleanup and finalization tasks are complete
- Validation that parent orchestrator requirements are satisfied

### Workflow Results Communication

The orchestrator must provide comprehensive results including:
- Complete state graph execution summary with transition history
- Detailed results from all TestGraphOrchestrated agents
- Comprehensive test execution metrics and quality assessments
- Test environment status and resource utilization reports
- Workflow performance metrics and optimization recommendations
- Structured recommendations for parent DeepCodeOrchestrator consumption

### Performance and Quality Metrics

The orchestrator completion must include validation of:
- Workflow execution time within acceptable performance bounds
- Resource utilization efficiency meeting established targets
- Test quality metrics achieving defined minimum standards
- Agent coordination efficiency meeting orchestration benchmarks
- Error handling effectiveness validated through proper recovery
- Workflow scalability and reliability demonstrated through execution
```
