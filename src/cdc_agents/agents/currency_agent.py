from typing import Any, Dict, AsyncIterable

import httpx
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool

from cdc_agents.agent.agent import A2AAgent, ResponseFormat

# example agent from google

@tool
def get_exchange_rate(
        currency_from: str = "USD",
        currency_to: str = "EUR",
        currency_date: str = "latest",
):
    """Use this to get current exchange rate.

    Args:
        currency_from: The currency to convert from (e.g., "USD").
        currency_to: The currency to convert to (e.g., "EUR").
        currency_date: The date for the exchange rate or "latest". Defaults to "latest".

    Returns:
        A dictionary containing the exchange rate data, or an error message if the request fails.
    """
    try:
        response = httpx.get(
            f"https://api.frankfurter.app/{currency_date}",
            params={"from": currency_from, "to": currency_to},
        )
        response.raise_for_status()

        data = response.json()
        if "rates" not in data:
            return {"error": "Invalid API response format."}
        return data
    except httpx.HTTPError as e:
        return {"error": f"API request failed: {e}"}
    except ValueError:
        return {"error": "Invalid JSON response from API."}

class CurrencyAgent(A2AAgent):

    SYSTEM_INSTRUCTION = (
        "You are a specialized assistant for currency conversions. "
        "Your sole purpose is to use the 'get_exchange_rate' tool to answer questions about currency exchange rates. "
        "If the user asks about anything other than currency conversion or exchange rates, "
        "politely state that you cannot help with that topic and can only assist with currency-related queries. "
        "Do not attempt to answer unrelated questions or use tools for other purposes."
        "Set response status to input_required if the user needs to provide more information."
        "Set response status to error if there is an error while processing the request."
        "Set response status to completed if the request is complete."
    )

    def __init__(self):
        A2AAgent.__init__(self, None, [get_exchange_rate], self.SYSTEM_INSTRUCTION)

    def invoke(self, query, sessionId) -> str:
        config = {"configurable": {"thread_id": sessionId}}
        self.graph.invoke({"messages": [("user", query)]}, config)
        return self.get_agent_response(config)

    async def stream(self, query, sessionId, graph=None) -> AsyncIterable[Dict[str, Any]]:
        return self.stream_agent_response_graph(query, sessionId, self.graph)


    def get_agent_response(self, config, graph=None):
        return self.get_agent_response_graph(config, self.graph)

    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]
