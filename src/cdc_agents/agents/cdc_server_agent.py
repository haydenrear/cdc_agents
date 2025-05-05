import dataclasses
import enum
import typing
from typing import Any, Dict, AsyncIterable

import injector
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver

from cdc_agents.agent.agent import A2AAgent, A2AReactAgent
from cdc_agents.agents.deep_code_research_agent import DeepResearchOrchestrated
from cdc_agents.config.agent_config_props import AgentConfigProps, AgentCardItem
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
    branch: str
    url: str
    repoStatus: typing.List[RepoStatus]
    error: typing.List[Error]
    serverSessionKey: ServerSessionKey

@tool
def perform_git_actions(actions_to_perform: typing.List[str] | str | typing.List[GitAction],
                        git_repo_url: str, git_branch: str,
                        perform_ops_async: bool) -> GitRepoResult:
    """Use this to embed a git repository for code context.

    Args:
        git_repo_url: the git repo URL for the repository to embed.
        git_branch: the branch of the repository to embed.
        actions_to_perform: a list of actions to perform.
            Options are:
             - 'ADD_BRANCH': add a single branch for a repository
             - 'REMOVE_BRANCH': remove a single branch
             - 'REMOVE_REPO': remove the repository
             - 'PARSE_BLAME_TREE': add additional embeddings based on parsing the git blame tree
             - 'SET_EMBEDDINGS': add the commit diff embeddings to the database
             - 'ADD_REPO': add an entire repository
        perform_ops_async: whether to return immediately or wait until all operations are completed
    Returns: a result object containing information about the operations completed
    """
    raise NotImplementedError()

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


@tool
def retrieve_commit_diff_code_context(git_repos: typing.List[GitRepo],
                                      query: str) -> CommitDiffFileResult:
    """Use this to retrieve information from repositories, with a diff history in XML form, related to a query code or embedding. This information can then be used for downstream code generation tasks as a source of context the model can use, or to otherwise inform development efforts.

    Args:
        git_repos: a list of git repositories to sample from. These should have been previously embedded using perform_git_actions function.
        query: a code snippet or embedding to use to condition the response. Will be used to search the database for related commit diffs.

    Returns:
        a result object containing a list of source files, with the source field containing the XML delimited history of the source code, up to the current state of the file.
    """
    raise NotImplementedError()

@tool
def retrieve_next_code_commit():
    """
    """
    pass

@tool
def apply_code_commit():
    """
    """
    pass

@tool
def retrieve_and_apply_code_commit():
    """
    """
    pass

@tool
def retrieve_current_repository_state():
    """
    """
    pass

@component(bind_to=[DeepResearchOrchestrated, A2AAgent, A2AReactAgent])
@injectable()
class CdcCodeSearchAgent(DeepResearchOrchestrated, A2AReactAgent):

    SYSTEM_INSTRUCTION = (
        """
        You are a specialized assistant for searching for code context information.
        Your overall goal is to provide context for code generation across multiple repositories, within the context of
        the history of the development of that software. In order to achieve your purpose, you have access to some tools.
        The tools you have facilitate performing operations on git repositories, including adding git diffs for repositories
        and branches to the vector database, removing git diffs for repositories and branches from the vector database,
        and retrieving files from the vector database with their history by a code snippet or commit message. You can 
        also parse the repository history with respect to an input, such as a code snippet or a message, and add diffs
        from the blame tree with respect to this code snippet or message.  
        
        If you do not have enough 
        information to perform your request, you can return a request for that information. Examples of this would be,
        for instance, if you need to include the code from one of the libraries. Then you could request for the URL
        for the git repository for that library. At that point, another agent will retrieve that information for you and 
        you can then perform your function to better inform your operations.
        """
    )

    @injector.inject
    def __init__(self, agent_config: AgentConfigProps, memory_saver: MemorySaver, model_provider: ModelProvider):
        A2AReactAgent.__init__(self, agent_config, [retrieve_commit_diff_code_context, perform_git_actions],
                               self.SYSTEM_INSTRUCTION, memory_saver, model_provider)

    @property
    def orchestrator_prompt(self):
        return """
        An agent that can add git repositories to an embedding database with history. This agent has a mechanism to 
        provide contextual information from the git repositories. This agent has access to an embedding database, so 
        he embeds the commit history as git commit diffs, and then interfaces with these repositories, returning 
        relevant files to the queries in the context with their history in an XML format that can be parsed by downstream
        codegen processes. It can also parse repositories with respect to particular queries, adding commit diffs to the 
        repository with respect to particular code, so it can be used to produce more relevant contextual information,
        using the git blame tree mechanism.
        """

    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]


@component(bind_to=[DeepResearchOrchestrated, A2AAgent, A2AReactAgent])
@injectable()
class CdcCodegenAgent(DeepResearchOrchestrated, A2AReactAgent):

    SYSTEM_INSTRUCTION = (
        """
        You are a specialized assistant for generating commits for implementation of software projects.
        You request the generation of a full git commit, with respect to a commit message and other contextual information 
        provided to you. 
        """
    )

    @injector.inject
    def __init__(self, agent_config: AgentConfigProps, memory_saver: MemorySaver, model_provider: ModelProvider):
        A2AReactAgent.__init__(self,agent_config, [retrieve_next_code_commit, apply_code_commit, retrieve_and_apply_code_commit],
                               self.SYSTEM_INSTRUCTION, memory_saver, model_provider)

    @property
    def orchestrator_prompt(self):
        return """
        An agent that generates code modifications using the history of diffs added with the CdcCodeSearchAgent.
        """

    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]