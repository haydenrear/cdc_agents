```properties
Version=0.0.1
AgentName=TestGraphCdcCodeSearchAgent
PromptType=Completion Definition
```

## TestGraphCdcCodeSearchAgent Completion Definition

```prompt_markdown
## TestGraphCdcCodeSearchAgent Completion Definition

The TestGraphCdcCodeSearchAgent is considered **complete** when one of the following conditions is met:

### Primary Completion Criteria

1. **Test Discovery Complete**: The agent has successfully discovered and analyzed all requested test-related code and artifacts, including:
   - All existing test implementations identified and catalogued
   - Test configuration files located and analyzed for completeness
   - Test dependencies mapped with version compatibility assessment
   - Test data files, fixtures, and resources inventoried
   - Test utilities and helper libraries documented
   - Test patterns and anti-patterns identified and classified

2. **Test Artifact Analysis Complete**: Comprehensive analysis of test artifacts has been completed, including:
   - Test execution logs and historical reports analyzed
   - Test coverage reports and metrics data processed
   - Test performance benchmarks and results evaluated
   - Test failure analysis and diagnostic artifacts reviewed
   - Test documentation and specifications catalogued
   - Test artifact relationships and dependencies mapped

3. **Test Configuration Analysis Complete**: All test configuration analysis has been finished, including:
   - Test environment configuration files identified and parsed
   - Test database connection and setup configurations analyzed
   - Test service configuration properties and settings documented
   - Test data source and fixture definitions inventoried
   - Test container and deployment configurations catalogued
   - Test CI/CD pipeline and build configurations analyzed

### Secondary Completion Indicators

- **Test Search Coverage**: The agent has achieved comprehensive search coverage including:
  - All requested test code patterns discovered and analyzed
  - Test framework usage and implementation approaches documented
  - Test structure and organization methodologies identified
  - Test naming conventions and classification schemes catalogued
  - Test dependency injection and mocking patterns analyzed
  - Test data management and fixture strategies documented

- **CDC Integration Success**: CDC integration has been properly completed including:
  - CDC schema leveraged for comprehensive test code indexing
  - Commit diff context used for targeted test impact analysis
  - CDC workflows integrated for automated test discovery
  - CDC-based test change impact assessment completed
  - Test artifact relationships maintained within CDC context
  - CDC-driven test prioritization and selection completed

- **Search Result Quality**: Search results meet established quality standards including:
  - Search results properly categorized by test type and functional area
  - Relevance scoring provided for all discovered test artifacts
  - Test dependency graphs and relationship mappings generated
  - Test coverage maps and gap analysis visualizations created
  - Test quality metrics and improvement recommendations produced
  - Test artifacts prioritized based on criticality and impact

### Incompletion Indicators

The agent should **NOT** be considered complete if:
- Critical test code or artifacts remain undiscovered or unanalyzed
- Test configuration analysis is incomplete or missing key components
- Search results lack proper categorization or relevance scoring
- Test dependency relationships are not properly mapped
- CDC integration is incomplete or not functioning correctly
- Test coverage analysis has significant gaps or inaccuracies
- Search performance is unacceptable or results are incomplete

### Termination Signals

The agent may terminate early if:
- Test repositories or codebases are completely inaccessible
- CDC server or database connectivity cannot be established
- Search infrastructure is unavailable or malfunctioning
- User explicitly requests search termination
- Maximum search execution time limits are exceeded
- Unrecoverable errors occur in the search process
- Search scope or criteria are fundamentally invalid or impossible

### Test Discovery Results Validation

The agent must validate completion through:
- Verification that all requested test patterns have been searched
- Confirmation that search results are comprehensive and accurate
- Validation that test artifact classifications are correct and complete
- Verification that test dependency mappings are accurate and current
- Confirmation that CDC integration is functioning properly
- Validation that search performance meets established benchmarks

### Search Results Communication

The agent must provide comprehensive search results including:
- Detailed test discovery reports with complete artifact inventories
- Test configuration analysis with recommendations for improvements
- Test coverage analysis with gap identification and prioritization
- Test quality assessment with improvement roadmaps and suggestions
- Test dependency graphs with impact analysis and recommendations
- Structured search results formatted for downstream agent consumption

### Integration with TestGraph Workflow

The agent completion must support test_graph workflow requirements including:
- Test discovery results properly formatted for test generation agents
- Test artifact analysis suitable for test building and execution agents
- Test configuration insights available for test environment preparation
- Test coverage analysis supporting test validation and reporting
- Test quality metrics enabling test optimization and improvement
- Search context maintained for subsequent test_graph workflow phases

### Quality Assurance Metrics

The agent completion must meet established quality criteria including:
- Search recall rates above defined minimum thresholds
- Search precision maintaining acceptable false positive rates
- Search performance within established execution time limits
- Result categorization accuracy meeting quality standards
- Test dependency mapping completeness and accuracy validated
- CDC integration reliability and consistency verified
```
