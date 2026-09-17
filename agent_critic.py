import json
import logging
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, MODEL_NAME
from prompts import CRITIC_PROMPT

logger = logging.getLogger(__name__)

critic_llm = ChatOpenAI(
    model=MODEL_NAME,
    openai_api_key=OPENROUTER_API_KEY,
    openai_api_base=OPENROUTER_BASE_URL,
    temperature=0.0,
)

def critic_node(state: dict):
    last_message = state["messages"][-1].content
    
    response = critic_llm.invoke([
        SystemMessage(content=CRITIC_PROMPT),
        HumanMessage(content=f"Review this draft:\n\n{last_message}")
    ])

    try:
        content = response.content.strip()
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        eval_data = json.loads(content)
    except Exception as e:
        logger.error(f"Critic JSON parse error: {e}")
        eval_data = {"is_approved": False, "feedback": "Format error. Please rewrite and ensure clarity."}

    is_approved = eval_data.get("is_approved", False)
    feedback = eval_data.get("feedback", "")
    current_revisions = state.get("revision_count", 0)
    
    if is_approved or current_revisions >= 2: 
        return {"revision_count": current_revisions + 1}
    else:
        rejection_msg = HumanMessage(content=f"CRITIC FEEDBACK: {feedback}\nPlease use your tools to fix this and generate a new draft.")
        return {
            "messages": [rejection_msg],
            "revision_count": current_revisions + 1,
            "step_count": 0,       
            "tool_call_count": 0 
        }