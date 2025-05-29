import typing
from typing import Any, TypeVar, Union, List, Optional

import injector
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import InjectedStore, InjectedState
from typing_extensions import Annotated

from cdc_agents.agent.a2a import A2AAgent
from cdc_agents.agent.agent import A2AReactAgent
from cdc_agents.agents.deep_code_research_agent import DeepResearchOrchestrated
from cdc_agents.common.graphql_models import (
    Error as GraphQLError,
    ServerSessionKey,
    GitRepoResult,
    GitRepoQueryRequest,
    GitBranch,
    GitRepo as GitRepoModel,
    SessionKey,
    ServerCommitMessage,
    GitRepoPromptingRequest,
    NextCommit,
    GitStagedResult,
    StagedOut,
    CodeQuery,
    CommitDiffFileResult,
    RepoStatus,
    CdcGitRepoBranch,
    GitAction,
    GitRepoRequestOptions,
    PromptingOptions,
    GitRepo, execute_graphql_request
)
from cdc_agents.config.agent_config_props import AgentConfigProps, AgentCardItem
from cdc_agents.config.cdc_server_config_props import CdcServerConfigProps
from cdc_agents.model_server.model_provider import ModelProvider
from cdc_agents.tools.tool_call_decorator import ToolCallDecorator
from python_di.configs.autowire import injectable
from python_di.configs.component import component
from python_util.logger.logger import LoggerFacade

T = TypeVar('T')

def _get_err(e):
    return GraphQLError(message=f"Failed to retrieve commit diff context: {str(e)}")

def _git_repo_result_err(repo_):
    return GitRepoResult(error=[GraphQLError(message=repo_)])

def _build_git_repo_prompting_req(git_branch, git_repo_url, query, session_id, git_repos=None):
    # Create request with Pydantic models
    request = GitRepoPromptingRequest(
        gitRepo=GitRepoModel(path=git_repo_url),
        branchName=git_branch,
        sessionKey=SessionKey(key=session_id),
        codeQuery=CodeQuery(codeString=query),
        gitRepoRequestOptions=GitRepoRequestOptions(
            promptingOptions=PromptingOptions(includeRepoClosestCommits=[
                GitRepoQueryRequest(gitRepo=GitRepo(path=git_repo.git_repo_url),
                                    gitBranch=GitBranch(branch=git_repo.git_branch))
                for git_repo in git_repos[1:]]
            if git_repos and isinstance(git_repos, typing.List) and len(git_repos) > 1
            else None)))
    return request





@component()
@injectable()
class CdcServerAgentToolCallProvider:

    @injector.inject
    def __init__(self, cdc_server: CdcServerConfigProps, tool_call_decorator: ToolCallDecorator):
        self.tool_call_decorator = tool_call_decorator
        self.cdc_server = cdc_server

    def produce_perform_commit_diff_context_git_actions(self):
        @tool
        def perform_commit_diff_context_git_actions(actions_to_perform: Union[List[str], str, List[GitAction]],
                                                    git_repo_url: str,
                                                    session_id: Annotated[str, InjectedState("session_id")],
                                                    git_branch: str = "main",
                                                    perform_ops_async: bool = True) -> GitRepoResult:
            """Use this to embed a git repository for code context. If you would like to add a branch and set the embeddings, pass a list in actions_to_perform [ADD_BRANCH, SET_EMBEDDINGS, PARSE_BLAME_TREE]. If you do not pass perform_ops_async, this operation will take hours, but the server can respond while it's processing if you pass perform_ops_async.

            Args:
                git_repo_url: the git repo URL for the repository to embed.
                git_branch: the branch of the repository to embed.
                actions_to_perform: a list of actions to perform.
                    Options are:
                     - 'ADD_BRANCH': add commit diffs for a single branch to the repository - does not embed changes
                     - 'REMOVE_BRANCH': remove a single branch from the commit diff vector database
                     - 'REMOVE_REPO': remove the repository from the commit diff vector database
                     - 'PARSE_BLAME_TREE': add additional embeddings based on parsing the git blame tree
                     - 'SET_EMBEDDINGS': set commit diff embeddings to the database
                     - 'ADD_REPO': add an entire repository for the commit diff vector database
                perform_ops_async: whether to return immediately or wait until all operations are completed
            Returns: a result object containing information about the operations completed
            """


            if not git_repo_url:
                return _git_repo_result_err(
                    "No git repo URL provided. Cannot perform git code search operation without location of said repository.")

            if isinstance(actions_to_perform, str):
                operations = [actions_to_perform]
            elif isinstance(actions_to_perform, list):
                if all(isinstance(action, str) for action in actions_to_perform):
                    operations = actions_to_perform
                else:
                    operations = [action.value if isinstance(action, GitAction) else str(action)
                                  for action in actions_to_perform]
            else:
                return _git_repo_result_err("""No valid operation provided. Could not call server with nothing to do. 
                                               Options are ADD_BRANCH, REMOVE_BRANCH, REMOVE_REPO, PARSE_BLAME_TREE, SET_EMBEDDINGS, ADD_REPO.""")

            # Construct GraphQL query
            query = """
            mutation PerformGitActions($request: GitRepositoryRequest!) {
                doGit(repoRequest: $request) {
                    branch
                    url
                    repoStatus
                    error {
                        message
                    }
                    sessionKey {
                        key
                    }
                    clientServerDiffs {
                        items {
                            value
                        }
                        numDiffs
                    }
                }
            }
            """

            # Construct variables
            variables = {
                "request": {
                    "operation": operations,
                    "gitBranch": {
                        "branch": git_branch
                    },
                    "gitRepo": {
                        "path": git_repo_url
                    },
                    "async": perform_ops_async,
                    "sessionKey": {
                        "key": session_id
                    }
                }
            }

            try:
                return execute_graphql_request(
                    endpoint=self.cdc_server.graphql_endpoint,
                    query=query,
                    variables=variables,
                    result_key="doGit",
                    model_class=GitRepoResult
                )
            except Exception as e:
                return GitRepoResult(
                    branch="",
                    url="",
                    repoStatus=[RepoStatus.FAIL],
                    error=[GraphQLError(message=f"Failed to execute Git operations: {str(e)}")],
                    sessionKey=ServerSessionKey(key="")
                )

        return perform_commit_diff_context_git_actions

    def produce_retrieve_commit_diff_code_context(self):
        @tool
        def retrieve_commit_diff_code_context(session_id: Annotated[str, InjectedState("session_id")],
                                              query: str, git_repo_url: str,
                                              context_repos: typing.List[CdcGitRepoBranch] = None,
                                              git_branch: str = "main") -> CommitDiffFileResult:
            """Use this to retrieve information from repositories, with a diff history in XML form, related to a query code or embedding. This information can then be used for downstream code generation tasks as a source of context the model can use, or to otherwise inform development efforts. Use this to search for code and files that have been embedded.

            Args:
                git_repo_url: the git repo for which to retrieve code context
                git_branch: the branch in the git repo for which to retrieve code context
                context_repos: a list of additional git repositories to consider when retrieving code context
                query: a code snippet or embedding to use to condition the response. Will be used to search the database for related commit diffs.

            Returns:
                a result object containing a list of source files, with the source field containing the XML delimited history of the source code, up to the current state of the file.
            """

            query_mutation = """
            mutation RetrieveCommitDiffContext($request: GitRepoPromptingRequest!) {
                buildCommitDiffContext(commitDiffContextRequest: $request) {
                    files {
                        path
                        source
                    }
                    errs {
                        message
                    }
                    sessionKey {
                        key
                    }
                }
            }
            """

            if not git_repo_url or not git_branch:
                return CommitDiffFileResult(
                    errs=[GraphQLError(message="No git repositories provided")],
                    files=[],
                    sessionKey=ServerSessionKey(key=session_id))

            request = _build_git_repo_prompting_req(git_branch, git_repo_url, query,
                                                    session_id, context_repos)

            try:
                return execute_graphql_request(
                    endpoint=self.cdc_server.graphql_endpoint,
                    query=query_mutation,
                    variables={"request": request.model_dump(exclude_none=True)},
                    result_key="buildCommitDiffContext",
                    model_class=CommitDiffFileResult)
            except Exception as e:
                return CommitDiffFileResult(
                    errs=[_get_err(e)],
                    files=[],
                    sessionKey=ServerSessionKey(key=session_id))

        return retrieve_commit_diff_code_context


    def produce_retrieve_next_code_commit(self):
        @tool
        def retrieve_next_code_commit(git_repo_url: str,
                                      session_id: Annotated[str, InjectedState("session_id")],
                                      branch_name: Optional[str] = None,
                                      query: Optional[str] = None) -> NextCommit:
            """Retrieve the next code commit recommendation.

            Args:
                git_repo_url: Git repository information.
                branch_name: The branch name to work with.
                query: Optional code query to condition the commit recommendation.

            Returns:
                Next commit information including diffs and commit message.
            """

            query_mutation = """
            mutation RetrieveNextCodeCommit($request: GitRepoPromptingRequest!) {
                doCommit(gitRepoPromptingRequest: $request) {
                    diffs {
                        newPath
                        oldPath
                        diffType
                        content {
                            content
                            hunks {
                                commitDiffEdits {
                                    diffType
                                    contentChange
                                }
                            }
                        }
                    }
                    commitMessage {
                        value
                    }
                    sessionKey {
                        key
                    }
                    errors {
                        message
                    }
                }
            }
            """

            request = _build_git_repo_prompting_req(branch_name, git_repo_url, query, session_id)

            try:
                return execute_graphql_request(
                    endpoint=self.cdc_server.graphql_endpoint,
                    query=query_mutation,
                    variables={"request": request.model_dump(exclude_none=True)},
                    result_key="doCommit",
                    model_class=NextCommit
                )
            except Exception as e:
                LoggerFacade.error(f"GraphQL request failed: {str(e)}")
                return NextCommit(
                    diffs=[],
                    commitMessage=ServerCommitMessage(value=""),
                    errors=[GraphQLError(message=f"Failed to retrieve next code commit: {str(e)}")]
                )

        return retrieve_next_code_commit


    def produce_retrieve_and_apply_code_commit(self):
        @tool
        def retrieve_and_apply_code_commit(git_repo_url: str,
                                           session_id: Annotated[str, InjectedState("session_id")],
                                           branch_name: Optional[str] = None,
                                           query: Optional[str] = None) -> NextCommit:
            """Retrieve and apply a code commit in a single operation.

            Args:
                git_repo_url: Git repository information.
                branch_name: The branch name to work with.
                query: Optional code query to condition the commit recommendation.

            Returns:
                Result of retrieving and applying the commit.
            """

            query_mutation = """
            mutation RetrieveAndApplyCodeCommit($request: GitRepoPromptingRequest!) {
                doCommit(gitRepoPromptingRequest: $request) {
                    diffs {
                        newPath
                        oldPath
                        diffType
                        content {
                            content
                        }
                    }
                    commitMessage {
                        value
                    }
                    sessionKey {
                        key
                    }
                    errors {
                        message
                    }
                }
            }
            """

            # Create request with Pydantic models
            request = GitRepoPromptingRequest(
                gitRepo=GitRepoModel(path=git_repo_url),
                branchName=branch_name,
                sessionKey=SessionKey(key=session_id),
                codeQuery=CodeQuery(codeString=query) if query is not None else None)

            try:
                next_commit = execute_graphql_request(
                    endpoint=self.cdc_server.graphql_endpoint,
                    query=query_mutation,
                    variables={"request": request.model_dump(exclude_none=True)},
                    result_key="doCommit",
                    model_class=NextCommit)

                applied = self._do_apply_last_staged(branch_name, git_repo_url, session_id, self.cdc_server)

                if len(applied.error) != 0:
                    next_commit.errors.extend(applied.error)

                return next_commit
            except Exception as e:
                LoggerFacade.error(f"GraphQL request failed: {str(e)}")
                return NextCommit(
                    diffs=[],
                    commitMessage=ServerCommitMessage(value=""),
                    errors=[GraphQLError(message=f"Failed to retrieve and apply code commit: {str(e)}")])

        return retrieve_and_apply_code_commit


    def produce_retrieve_current_repository_staged(self):
        @tool
        def retrieve_current_repository_staged(git_repo_url: str,
                                               session_id: Annotated[str, InjectedState("session_id")],
                                               branch_name: Optional[str] = None) -> GitStagedResult:
            """Retrieve current staged changes in the repository.

            Args:
                git_repo_url: Git repository information.
                branch_name: The branch name to get staged changes from.

            Returns:
                Current staged changes in the repository.
            """

            query = """
            mutation GetStaged($request: GitRepoQueryRequest!) {
                getStaged(repoRequest: $request) {
                    staged {
                        files {
                            beforeApplyDiff {
                                name
                                linesWithLineNumbers
                            }
                            afterApplyDiff {
                                name
                                linesWithLineNumbers
                            }
                        } 
                    }
                    error {
                        message
                    }
                    sessionKey {
                        key
                    }
                }
            }
            """


            if git_repo_url is None:
                return GitStagedResult(
                    staged=StagedOut(files=[]),
                    sessionKey=ServerSessionKey(key=session_id),
                    error=[GraphQLError(message=f"Could not retrieve current repository staged - no git_repo_url provided.")])

            if branch_name is None:
                branch_name = "main"

            # Create request with Pydantic models
            request = GitRepoQueryRequest(
                gitRepo=GitRepoModel(path=git_repo_url),
                gitBranch=GitBranch(branch=branch_name),
                sessionKey=SessionKey(key=session_id))

            try:
                return execute_graphql_request(
                    endpoint=self.cdc_server.graphql_endpoint,
                    query=query,
                    variables={"request": request.model_dump(exclude_none=True)},
                    result_key="getStaged",
                    model_class=GitStagedResult
                )
            except Exception as e:
                LoggerFacade.error(f"GraphQL request failed: {str(e)}")
                return GitStagedResult(
                    staged=StagedOut(files=[]),
                    sessionKey=ServerSessionKey(key=session_id),
                    error=[GraphQLError(message=f"Failed to retrieve staged changes: {str(e)}")]
                )

        return retrieve_current_repository_staged


    def _do_apply_last_staged(self, branch_name, git_repo_url, session_id, cdc_server):
        query = """
        mutation ApplyLastStaged($request: GitRepoQueryRequest!) {
            applyLastStaged(repoRequest: $request) {
                staged {
                    files {
                        beforeApplyDiff {
                            name
                            linesWithLineNumbers
                        }
                        afterApplyDiff {
                            name
                            linesWithLineNumbers
                        }
                    } 
                }
                error {
                    message
                }
                sessionKey {
                    key
                }
            }
        }
        """
        # Create request with Pydantic models
        request = GitRepoQueryRequest(
            gitRepo=GitRepoModel(path=git_repo_url),
            gitBranch=GitBranch(branch=branch_name),
            sessionKey=SessionKey(key=session_id))

        try:
            return execute_graphql_request(
                endpoint=self.cdc_server.graphql_endpoint,
                query=query,
                variables={"request": request.model_dump(exclude_none=True)},
                result_key="applyLastStaged",
                model_class=GitStagedResult
            )
        except Exception as e:
            return GitStagedResult(
                staged=StagedOut(files=[]),
                sessionKey=ServerSessionKey(key=session_id),
                error=[GraphQLError(message=f"Failed to apply staged changes: {str(e)}")]
            )


    def produce_apply_last_staged(self):
        @tool
        def apply_last_staged(git_repo_url: str,
                              session_id: Annotated[str, InjectedState("session_id")],
                              branch_name: Optional[str] = None) -> GitStagedResult:
            """Apply changes created last in the commit diff context session

            Args:
                git_repo_url: Git repository information.
                branch_name: The branch name to get staged changes from.

            Returns:
                Apply the staged changes from the last next commit call to the repository so the code can be tested and ran
            """

            return self._do_apply_last_staged(branch_name, git_repo_url, session_id, self.cdc_server)

        return apply_last_staged


    def produce_reset_any_staged(self):
        @tool
        def reset_any_staged(git_repo_url: str,
                             session_id: Annotated[str, InjectedState("session_id")],
                             branch_name: Optional[str] = None) -> GitStagedResult:
            """Reset the repository from any application of staged.

            Args:
                git_repo_url: Git repository information.
                branch_name: The branch name to get staged changes from.

            Returns:
                If any changes are staged in the repository, reset them. This will return the changes that were staged.
            """

            query = """
            mutation ResetAnyStaged($request: GitRepoQueryRequest!) {
                resetAnyStaged(repoRequest: $request) {
                    staged {
                        files {
                            beforeApplyDiff {
                                name
                                linesWithLineNumbers
                            }
                            afterApplyDiff {
                                name
                                linesWithLineNumbers
                            }
                        } 
                    }
                    error {
                        message
                    }
                    sessionKey {
                        key
                    }
                }
            }
            """

            # Create request with Pydantic models
            request = GitRepoQueryRequest(
                gitRepo=GitRepoModel(path=git_repo_url),
                gitBranch=GitBranch(branch=branch_name),
                sessionKey=SessionKey(key=session_id))

            try:
                return execute_graphql_request(
                    endpoint=self.cdc_server.graphql_endpoint,
                    query=query,
                    variables={"request": request.model_dump(exclude_none=True)},
                    result_key="resetAnyStaged",
                    model_class=GitStagedResult)
            except Exception as e:
                LoggerFacade.error(f"GraphQL request failed: {str(e)}")
                return GitStagedResult(
                    staged=StagedOut(files=[]),
                    sessionKey=ServerSessionKey(key=session_id),
                    error=[GraphQLError(message=f"Failed to reset staged changes: {str(e)}")])

        return reset_any_staged


@component(bind_to=[DeepResearchOrchestrated, A2AAgent, A2AReactAgent])
@injectable()
class CdcCodeSearchAgent(DeepResearchOrchestrated, A2AReactAgent):

    @injector.inject
    def __init__(self, agent_config: AgentConfigProps, memory_saver: MemorySaver, model_provider: ModelProvider,
                 cdc_server: CdcServerConfigProps, tool_call_provider: CdcServerAgentToolCallProvider):
        self.tool_call_provider = tool_call_provider
        self_card: AgentCardItem = agent_config.agents[self.__class__.__name__]
        DeepResearchOrchestrated.__init__(self, self_card)
        A2AReactAgent.__init__(self, agent_config,
                               [
                                  self.tool_call_provider.produce_retrieve_commit_diff_code_context(),
                                  self.tool_call_provider.produce_retrieve_current_repository_staged(),
                                  self.tool_call_provider.produce_apply_last_staged(),
                                  self.tool_call_provider.produce_reset_any_staged(),
                                  self.tool_call_provider.produce_perform_commit_diff_context_git_actions()
                               ],
                               self_card.agent_descriptor.system_instruction, memory_saver, model_provider)


@component(bind_to=[DeepResearchOrchestrated, A2AAgent, A2AReactAgent])
@injectable()
class CdcCodegenAgent(DeepResearchOrchestrated, A2AReactAgent):

    @injector.inject
    def __init__(self, agent_config: AgentConfigProps, memory_saver: MemorySaver,
                 model_provider: ModelProvider, cdc_server: CdcServerConfigProps, tool_call_provider: CdcServerAgentToolCallProvider):
        self.tool_call_provider = tool_call_provider
        self_card: AgentCardItem = agent_config.agents[self.__class__.__name__]
        DeepResearchOrchestrated.__init__(self, self_card)
        A2AReactAgent.__init__(self, agent_config,
                               [
                                   self.tool_call_provider.produce_retrieve_next_code_commit(),
                                   self.tool_call_provider.produce_retrieve_and_apply_code_commit()
                               ],
                               self_card.agent_descriptor.system_instruction, memory_saver, model_provider)
