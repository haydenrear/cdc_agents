import dataclasses
import enum
import typing
from typing import Any, Dict, AsyncIterable

import injector
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver

from cdc_agents.agent.agent import A2AReactAgent
from cdc_agents.agent.a2a import A2AAgent
from cdc_agents.agents.deep_code_research_agent import DeepResearchOrchestrated
from cdc_agents.config.agent_config_props import AgentConfigProps, AgentCardItem
from cdc_agents.config.cdc_server_config_props import CdcServerConfigProps
from cdc_agents.model_server.model_provider import ModelProvider
from python_di.configs.autowire import injectable
from python_di.configs.component import component


class GitAction(enum.Enum):
    ADD_BRANCH = 0
    REMOVE_BRANCH = 1
    REMOVE_REPO = 2
    PARSE_BLAME_TREE = 3
    SET_EMBEDDINGS = 4
    ADD_REPO = 5

class RepoStatus(enum.Enum):
    ADDED = 0
    REMOVED = 1
    FAIL = 2
    ASYNC = 3

@dataclasses.dataclass(init=True)
class Error:
    message: str

@dataclasses.dataclass(init=True)
class ServerSessionKey:
    key: str

@dataclasses.dataclass(init=True)
class GitRepoValidatableDiffItem:
    value: str

@dataclasses.dataclass(init=True)
class GitRepoValidatableDiff:
    items: typing.List[GitRepoValidatableDiffItem]
    numDiffs: int

@dataclasses.dataclass(init=True)
class GitRepoResult:
    branch: str = None
    url: str = None
    repoStatus: typing.List[RepoStatus] = None
    error: typing.List[Error] = None
    serverSessionKey: ServerSessionKey = None

def produce_perform_commit_diff_context_git_actions(cdc_server: CdcServerConfigProps):

    @tool
    def perform_commit_diff_context_git_actions(actions_to_perform: typing.List[str] | str | typing.List[GitAction],
                                                git_repo_url: str, git_branch: str = "main",
                                                perform_ops_async: bool = True) -> GitRepoResult:
        """Use this to embed a git repository for code context.

        Args:
            git_repo_url: the git repo URL for the repository to embed.
            git_branch: the branch of the repository to embed.
            actions_to_perform: a list of actions to perform.
                Options are:
                 - 'ADD_BRANCH': add a single branch for a repository to the commit diff vector database
                 - 'REMOVE_BRANCH': remove a single branch from the commit diff vector database
                 - 'REMOVE_REPO': remove the repository from the commit diff vector database
                 - 'PARSE_BLAME_TREE': add additional embeddings based on parsing the git blame tree
                 - 'SET_EMBEDDINGS': set commit diff embeddings to the database
                 - 'ADD_REPO': add an entire repository for the commit diff vector database
            perform_ops_async: whether to return immediately or wait until all operations are completed
        Returns: a result object containing information about the operations completed
        """
        import requests

        if not git_repo_url:
            return _git_repo_result_err("No git repo URL provided. Cannot perform git code search operation without location of said repository.")


        if isinstance(actions_to_perform, str):
            operations = [actions_to_perform]
        elif isinstance(actions_to_perform, list):
            if all(isinstance(action, str) for action in actions_to_perform):
                operations = actions_to_perform
            else:  # Convert GitAction enum to string
                operations = [action for action in actions_to_perform]
        else:
            return _git_repo_result_err("""No valid operation provided. Could not call server with nothing to do. 
                                           Options are ADD_BRANCH, REMOVE_BRANCH, REMOVE_REPO, PARSE_BLAME_TREE, SET_EMBEDDING, ADD_REPO.""")

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
                "async": perform_ops_async
            }
        }

        # Make the GraphQL request
        endpoint = cdc_server.graphql_endpoint  # Replace with actual endpoint

        headers = {
            "Content-Type": "application/json",
        }

        data = {
            "query": query,
            "variables": variables
        }

        try:
            response = requests.post(endpoint, headers=headers, json=data)
            response.raise_for_status()
            result = response.json().get("data", {}).get("doGit", {})

            # Convert GraphQL response to GitRepoResult
            return GitRepoResult(
                branch=result.get("branch", ""),
                url=result.get("url", ""),
                repoStatus=[RepoStatus[status] for status in result.get("repoStatus", [])],
                error=[Error(message=err["message"]) for err in result.get("error", [])],
                serverSessionKey=ServerSessionKey(key=result.get("sessionKey", {}).get("key", ""))
            )
        except Exception as e:
            print(f"GraphQL request failed: {str(e)}")
            return GitRepoResult(
                branch="",
                url="",
                repoStatus=[RepoStatus.FAIL],
                error=[Error(message=f"Failed to execute Git operations: {str(e)}")],
                serverSessionKey=ServerSessionKey(key="")
            )

    return perform_commit_diff_context_git_actions


def _git_repo_result_err(repo_):
    return GitRepoResult(error=[Error(message=repo_)])


@dataclasses.dataclass(init=True)
class GitRepo:
    git_repo_url: str
    git_branch: str

@dataclasses.dataclass(init=True)
class CommitDiffFileItem:
    path: str
    source: str

@dataclasses.dataclass(init=True)
class CommitDiffFileResult:
    errs: typing.List[Error]
    files: typing.List

def produce_retrieve_commit_diff_code_context(cdc_server: CdcServerConfigProps):
    @tool
    def retrieve_commit_diff_code_context(git_repos: typing.List[GitRepo], query: str) -> CommitDiffFileResult:
        """Use this to retrieve information from repositories, with a diff history in XML form, related to a query code or embedding. This information can then be used for downstream code generation tasks as a source of context the model can use, or to otherwise inform development efforts.

        Args:
            git_repos: a list of git repositories to sample from. These should have been previously embedded using perform_git_actions function.
            query: a code snippet or embedding to use to condition the response. Will be used to search the database for related commit diffs.

        Returns:
            a result object containing a list of source files, with the source field containing the XML delimited history of the source code, up to the current state of the file.
        """
        import requests

        # Construct GraphQL query
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
            }
        }
        """

        # If no repositories provided, return error
        if not git_repos:
            return CommitDiffFileResult(
                errs=[Error(message="No git repositories provided")],
                files=[]
            )

        # Use the first repo for the request
        repo = git_repos[0]

        # Construct variables
        variables = {
            "request": {
                "gitRepo": {
                    "path": repo.git_repo_url
                },
                "branchName": repo.git_branch,
                "sessionKey": {
                    "key": "session-key"  # You would need to get this from somewhere
                },
                "codeQuery": {
                    "codeString": query
                }
            }
        }

        # Make the GraphQL request
        endpoint = cdc_server.graphql_endpoint  # Replace with actual endpoint

        headers = {
            "Content-Type": "application/json",
        }

        data = {
            "query": query_mutation,
            "variables": variables
        }

        try:
            response = requests.post(endpoint, headers=headers, json=data)
            response.raise_for_status()
            result = response.json().get("data", {}).get("buildCommitDiffContext", {})

            # Convert GraphQL response to CommitDiffFileResult
            return CommitDiffFileResult(
                files=[CommitDiffFileItem(path=file["path"], source=file["source"])
                       for file in result.get("files", [])],
                errs=[Error(message=err["message"]) for err in result.get("errs", [])]
            )
        except Exception as e:
            print(f"GraphQL request failed: {str(e)}")
            return CommitDiffFileResult(
                errs=[Error(message=f"Failed to retrieve commit diff context: {str(e)}")],
                files=[]
            )
    return retrieve_commit_diff_code_context

def produce_retrieve_next_code_commit(cdc_server: CdcServerConfigProps):
    @tool
    def retrieve_next_code_commit(git_repo: GitRepo, branch_name: str, query: str = None):
        """Retrieve the next code commit recommendation.

        Args:
            git_repo: Git repository information.
            branch_name: The branch name to work with.
            query: Optional code query to condition the commit recommendation.

        Returns:
            Next commit information including diffs and commit message.
        """
        import requests

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

        variables = {
            "request": {
                "gitRepo": {
                    "path": git_repo.git_repo_url
                },
                "branchName": branch_name,
                "sessionKey": {
                    "key": "session-key"  # Replace with actual session key
                }
            }
        }

        if query:
            variables["request"]["codeQuery"] = {
                "codeString": query
            }

        # Make the GraphQL request
        endpoint = cdc_server.graphql_endpoint  # Replace with actual endpoint

        headers = {
            "Content-Type": "application/json",
        }

        data = {
            "query": query_mutation,
            "variables": variables
        }

        try:
            response = requests.post(endpoint, headers=headers, json=data)
            response.raise_for_status()
            return response.json().get("data", {}).get("doCommit", {})
        except Exception as e:
            print(f"GraphQL request failed: {str(e)}")
            return {"errors": [{"message": f"Failed to retrieve next code commit: {str(e)}"}]}
    return retrieve_next_code_commit

def produce_apply_code_commit(cdc_server: CdcServerConfigProps):
    @tool
    def apply_code_commit(git_repo: GitRepo, branch_name: str, diffs: typing.List[dict], commit_message: str):
        """Apply a code commit to the repository.

        Args:
            git_repo: Git repository information.
            branch_name: The branch name to apply the commit to.
            diffs: List of diff objects to apply.
            commit_message: Commit message for the applied changes.

        Returns:
            Result of applying the commit.
        """
        import requests

        query_mutation = """
        mutation ApplyCodeCommit($request: GitRepoPromptingRequest!) {
            doCommit(gitRepoPromptingRequest: $request) {
                diffs {
                    newPath
                    oldPath
                    diffType
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

        variables = {
            "request": {
                "gitRepo": {
                    "path": git_repo.git_repo_url
                },
                "branchName": branch_name,
                "commitMessage": {
                    "value": commit_message
                },
                "sessionKey": {
                    "key": "session-key"  # Replace with actual session key
                },
                "staged": {
                    "diffs": [{"underlyingDiff": diff} for diff in diffs]
                }
            }
        }

        # Make the GraphQL request
        endpoint = cdc_server.graphql_endpoint  # Replace with actual endpoint

        headers = {
            "Content-Type": "application/json",
        }

        data = {
            "query": query_mutation,
            "variables": variables
        }

        try:
            response = requests.post(endpoint, headers=headers, json=data)
            response.raise_for_status()
            return response.json().get("data", {}).get("doCommit", {})
        except Exception as e:
            print(f"GraphQL request failed: {str(e)}")
            return {"errors": [{"message": f"Failed to apply code commit: {str(e)}"}]}
    return apply_code_commit

def produce_retrieve_and_apply_code_commit(cdc_server: CdcServerConfigProps):
    @tool
    def retrieve_and_apply_code_commit(git_repo: GitRepo, branch_name: str, query: str = None):
        """Retrieve and apply a code commit in a single operation.

        Args:
            git_repo: Git repository information.
            branch_name: The branch name to work with.
            query: Optional code query to condition the commit recommendation.

        Returns:
            Result of retrieving and applying the commit.
        """
        import requests

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

        variables = {
            "request": {
                "gitRepo": {
                    "path": git_repo.git_repo_url
                },
                "branchName": branch_name,
                "sessionKey": {
                    "key": "session-key"  # Replace with actual session key
                },
                "applyCommit": True
            }
        }

        if query:
            variables["request"]["codeQuery"] = {
                "codeString": query
            }

        # Make the GraphQL request
        endpoint = cdc_server.graphql_endpoint  # Replace with actual endpoint

        headers = {
            "Content-Type": "application/json",
        }

        data = {
            "query": query_mutation,
            "variables": variables
        }

        try:
            response = requests.post(endpoint, headers=headers, json=data)
            response.raise_for_status()
            return response.json().get("data", {}).get("doCommit", {})
        except Exception as e:
            print(f"GraphQL request failed: {str(e)}")
            return {"errors": [{"message": f"Failed to retrieve and apply code commit: {str(e)}"}]}

    return retrieve_and_apply_code_commit

def produce_retrieve_current_repository_staged(cdc_server: CdcServerConfigProps):
    @tool
    def retrieve_current_repository_staged(git_repo: GitRepo, branch_name: str):
        """Retrieve current staged changes in the repository.

        Args:
            git_repo: Git repository information.
            branch_name: The branch name to get staged changes from.

        Returns:
            Current staged changes in the repository.
        """
        import requests

        query = """
        mutation GetStagedChanges($request: GitRepoPromptingRequest!) {
            buildCommitDiffContext(commitDiffContextRequest: $request) {
                files {
                    path
                    source
                }
                errs {
                    message
                }
            }
        }
        """

        variables = {
            "request": {
                "gitRepo": {
                    "path": git_repo.git_repo_url
                },
                "branchName": branch_name,
                "sessionKey": {
                    "key": "session-key"  # Replace with actual session key
                },
                "getStagedOnly": True  # Flag to indicate we want only staged changes
            }
        }

        # Make the GraphQL request
        endpoint = cdc_server.graphql_endpoint  # Replace with actual endpoint

        headers = {
            "Content-Type": "application/json",
        }

        data = {
            "query": query,
            "variables": variables
        }

        try:
            response = requests.post(endpoint, headers=headers, json=data)
            response.raise_for_status()
            return response.json().get("data", {}).get("buildCommitDiffContext", {})
        except Exception as e:
            print(f"GraphQL request failed: {str(e)}")
            return {"errs": [{"message": f"Failed to retrieve staged changes: {str(e)}"}]}

    return retrieve_current_repository_staged

@component(bind_to=[DeepResearchOrchestrated, A2AAgent, A2AReactAgent])
@injectable()
class CdcCodeSearchAgent(DeepResearchOrchestrated, A2AReactAgent):

    @injector.inject
    def __init__(self, agent_config: AgentConfigProps, memory_saver: MemorySaver, model_provider: ModelProvider,
                 cdc_server: CdcServerConfigProps):
        self_card: AgentCardItem = agent_config.agents[self.__class__.__name__]
        DeepResearchOrchestrated.__init__(self, self_card)
        A2AReactAgent.__init__(self, agent_config,
                               [produce_retrieve_commit_diff_code_context(cdc_server),
                                produce_retrieve_current_repository_staged(cdc_server),
                                produce_perform_commit_diff_context_git_actions(cdc_server)],
                               self_card.agent_descriptor.system_instruction, memory_saver, model_provider)

@component(bind_to=[DeepResearchOrchestrated, A2AAgent, A2AReactAgent])
@injectable()
class CdcCodegenAgent(DeepResearchOrchestrated, A2AReactAgent):

    @injector.inject
    def __init__(self, agent_config: AgentConfigProps, memory_saver: MemorySaver, model_provider: ModelProvider,
                 cdc_server: CdcServerConfigProps):
        self_card: AgentCardItem = agent_config.agents[self.__class__.__name__]
        DeepResearchOrchestrated.__init__(self, self_card)
        A2AReactAgent.__init__(self, agent_config,
                               [produce_retrieve_next_code_commit(cdc_server),
                                produce_apply_code_commit(cdc_server),
                                produce_retrieve_and_apply_code_commit(cdc_server)],
                               self_card.agent_descriptor.system_instruction, memory_saver, model_provider)