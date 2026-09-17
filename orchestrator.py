from typing import TypedDict, Annotated, Literal
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from agent_research import call_model as researcher_node
from agent_critic import critic_node
from tools_langchain import TOOLS

class MultiAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    step_count: int
    tool_call_count: int
    revision_count: int

def research_router(state: MultiAgentState) -> Literal["tools", "critic"]:
    last_message = state["messages"][-1]
    if getattr(last_message, "tool_calls", None):
        return "tools"
    return "critic"

def critic_router(state: MultiAgentState) -> Literal["researcher", "__end__"]:
    if isinstance(state["messages"][-1], HumanMessage):
        return "researcher"
    return END

workflow = StateGraph(MultiAgentState)

workflow.add_node("researcher", researcher_node)
workflow.add_node("tools", ToolNode(TOOLS))
workflow.add_node("critic", critic_node)

workflow.add_edge(START, "researcher")
workflow.add_conditional_edges("researcher", research_router, {"tools": "tools", "critic": "critic"})
workflow.add_edge("tools", "researcher")
workflow.add_conditional_edges("critic", critic_router, {"researcher": "researcher", END: END})

orchestrator = workflow.compile()