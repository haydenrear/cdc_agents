import abc
import array
import dataclasses
import enum
import typing
from typing import Any, Dict, AsyncIterable

import httpx
import injector
import torch
from array import ArrayType
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool

from cdc_agents.agent.agent import A2AAgent, ResponseFormat, BaseAgent
from cdc_agents.config.agent_config_props import AgentConfigProps, AgentCardItem
from python_di.configs.autowire import injectable
from python_di.configs.component import component
from python_di.inject.profile_composite_injector.scopes.prototype_scope import prototype_scope


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

class DeepResearchOrchestrated(BaseAgent, abc.ABC):
    """
    Marker interface for DI, marking the agents being orchestrated.
    """
    pass

@component(bind_to=[DeepResearchOrchestrated])
@injectable()
class CdcAgent(DeepResearchOrchestrated, A2AAgent):

    SYSTEM_INSTRUCTION = (
        """
        You are a specialized assistant for code context information.
        # Your sole purpose is to use the 'get_exchange_rate' tool to answer questions about currency exchange rates.
        # If the user asks about anything other than currency conversion or exchange rates,
        # politely state that you cannot help with that topic and can only assist with currency-related queries. 
        # Do not attempt to answer unrelated questions or use tools for other purposes.
        # Set response status to input_required if the user needs to provide more information.
        # Set response status to error if there is an error while processing the request.
        # Set response status to completed if the request is complete.
        """
    )

    @injector.inject
    def __init__(self, agent_config: AgentConfigProps):
        A2AAgent.__init__(self,
                          agent_config.agents['CdcAgent'].agent_descriptor.model if 'CdcAgent' in agent_config.agents.keys() else None,
                          [retrieve_commit_diff_code_context, perform_git_actions],
                          self.SYSTEM_INSTRUCTION)
        self.agent_config: AgentCardItem = agent_config.agents['CdcAgent'] \
            if 'CdcAgent' in agent_config.agents.keys() else None

    def invoke(self, query, sessionId) -> str:
        config = {"configurable": {"thread_id": sessionId}}
        self.graph.invoke({"messages": [("user", query)]}, config)
        return self.get_agent_response(config)

    async def stream(self, query, sessionId) -> AsyncIterable[Dict[str, Any]]:
        return self.stream_agent_response_graph(query, sessionId, self.graph)

    def get_agent_response(self, config):
        return self.get_agent_response_graph(config, self.graph)


    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]


