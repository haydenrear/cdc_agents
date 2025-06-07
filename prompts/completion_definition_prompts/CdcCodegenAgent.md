## CdcCodegenAgent Completion Definition

```prompt_markdown
## CdcCodegenAgent Completion Definition

The CdcCodegenAgent is considered **complete** when one of the following conditions is met:

### Primary Completion Criteria

1. **Code Generation Complete**: The agent has successfully generated all requested code artifacts, including:
   - Complete code files or modules generated according to specifications
   - Generated code compiles/validates without critical errors
   - Code structure and patterns align with project requirements
   - All requested functionality implemented in generated code

2. **Database Integration Success**: When using PostgreSQL tools, the agent has:
   - Successfully queried the repository database for relevant information
   - Retrieved accurate schema and metadata for code generation
   - Integrated database-driven templates and patterns effectively
   - Generated code that properly interfaces with existing data structures

3. **Code Quality Standards Met**: Generated code meets established quality requirements, including:
   - Follows project coding standards and conventions
   - Includes appropriate documentation and comments
   - Implements proper error handling and validation
   - Maintains consistency with existing codebase patterns

### Secondary Completion Indicators

- **Template Integration Success**: Code generation templates have been properly utilized including:
  - Database-driven templates applied correctly
  - Custom code patterns implemented accurately
  - Generated code structure matches template specifications
  - Template parameters resolved from database queries

- **Repository Database Connectivity**: PostgreSQL tool integration has provided valuable results including:
  - Successful connection to repository database
  - Accurate retrieval of metadata and schema information
  - Proper mapping of database entities to code structures
  - Effective use of repository information for code generation context

### Incompletion Indicators

The agent should **NOT** be considered complete if:
- Generated code contains compilation errors or critical bugs
- Database queries fail or return incomplete/incorrect information
- Generated code does not meet specified requirements or functionality
- Code quality standards are not satisfied
- Template application results in malformed or invalid code
- Required code artifacts are missing or incomplete
- Integration with existing codebase creates conflicts or incompatibilities

### Termination Signals

The agent may terminate early if:
- PostgreSQL database is unavailable or inaccessible
- Required database tables or schema information is missing
- Code generation templates are invalid or corrupted
- User explicitly requests code generation termination
- Maximum code generation complexity or size limits are exceeded
- Unrecoverable errors occur in the code generation process
```
