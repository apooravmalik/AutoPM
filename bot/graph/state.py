from typing import TypedDict, Dict

class AgentState(TypedDict):
    """
    Represents the state of our agent.
    """
    input: str      # The user's raw message
    action: str     # The action extracted by the LLM
    params: Dict    # The parameters for the action
    response: str   # The final message to send back to the user