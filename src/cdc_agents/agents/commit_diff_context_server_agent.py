import dataclasses
import enum
import typing
from typing import Any, Dict, AsyncIterable

import httpx
import injector
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool

from cdc_agents.agent.agent import A2AAgent, ResponseFormat
from cdc_agents.config.agent_config_props import AgentConfigProps, AgentCardItem
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
    """Use this to embed a git repository for code context

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
    pass

@tool
def retrieve_commit_diff_code_context():
    """Use this to get current exchange rate.

    Args:
        currency_from: The currency to convert from (e.g., "USD").
        currency_to: The currency to convert to (e.g., "EUR").
        currency_date: The date for the exchange rate or "latest". Defaults to "latest".

    Returns:
        A dictionary containing the exchange rate data, or an error message if the request fails.
    """
    try:
        return None
        # response.raise_for_status()
        #
        # data = response.json()
        # if "rates" not in data:
        #     return {"error": "Invalid API response format."}
        # return data
    except httpx.HTTPError as e:
        return {"error": f"API request failed: {e}"}
    except ValueError:
        return {"error": "Invalid JSON response from API."}

@component()
@injectable()
class CdcAgent(A2AAgent):

    SYSTEM_INSTRUCTION = (
        """
        You are a specialized assistant for code context information.
        Your sole purpose is to use the 'get_exchange_rate' tool to answer questions about currency exchange rates.
        If the user asks about anything other than currency conversion or exchange rates,
        politely state that you cannot help with that topic and can only assist with currency-related queries. 
        Do not attempt to answer unrelated questions or use tools for other purposes.
        Set response status to input_required if the user needs to provide more information.
        Set response status to error if there is an error while processing the request.
        Set response status to completed if the request is complete.
        """
    )

    @injector.inject
    def __init__(self, agent_config: AgentConfigProps):
        A2AAgent.__init__(self,
                          agent_config.agents['CdcAgent'].agent_descriptor.model if 'CdcAgent' in agent_config.agents.keys() else None,
                          [retrieve_commit_diff_code_context, perform_git_actions],
                          self.SYSTEM_INSTRUCTION)
        self.agent_config: AgentCardItem = agent_config['CdcAgent'] \
            if 'CdcAgent' in agent_config.agents.keys() else None

    def invoke(self, query, sessionId) -> str:
        config = {"configurable": {"thread_id": sessionId}}
        self.graph.invoke({"messages": [("user", query)]}, config)
        return self.get_agent_response(config)

    async def stream(self, query, sessionId) -> AsyncIterable[Dict[str, Any]]:
        inputs = {"messages": [("user", query)]}
        config = {"configurable": {"thread_id": sessionId}}

        for item in self.graph.stream(inputs, config, stream_mode="values"):
            message = item["messages"][-1]
            if (
                    isinstance(message, AIMessage)
                    and message.tool_calls
                    and len(message.tool_calls) > 0
            ):
                yield {
                    "is_task_complete": False,
                    "require_user_input": False,
                    "content": "Looking up the exchange rates...",
                }
            elif isinstance(message, ToolMessage):
                yield {
                    "is_task_complete": False,
                    "require_user_input": False,
                    "content": "Processing the exchange rates..",
                }

        yield self.get_agent_response(config)


    def get_agent_response(self, config):
        current_state = self.graph.get_state(config)
        structured_response = current_state.values.get('structured_response')
        if structured_response and isinstance(structured_response, ResponseFormat):
            if structured_response.status == "input_required":
                return {
                    "is_task_complete": False,
                    "require_user_input": True,
                    "content": structured_response.message
                }
            elif structured_response.status == "error":
                return {
                    "is_task_complete": False,
                    "require_user_input": True,
                    "content": structured_response.message
                }
            elif structured_response.status == "completed":
                return {
                    "is_task_complete": True,
                    "require_user_input": False,
                    "content": structured_response.message
                }

        return {
            "is_task_complete": False,
            "require_user_input": True,
            "content": "We are unable to process your request at the moment. Please try again.",
        }

    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]
