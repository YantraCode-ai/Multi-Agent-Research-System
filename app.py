import json
import streamlit as st
from langchain_core.messages import HumanMessage
from orchestrator import orchestrator

st.set_page_config(page_title="Multi Agent Researcher", page_icon="🕸️", layout="wide")
st.title("Multi Agent Researcher")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("E.g., Compare benchmark scores across top RAG papers..."):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"): 
        status_box = st.status("Executing...", expanded=True)
        final_answer = ""

        inputs = {"messages": [HumanMessage(content=prompt)]}
        
        for event in orchestrator.stream(inputs, stream_mode="updates"): 
            
            if "researcher" in event:
                message = event["researcher"]["messages"][-1]
                
                if hasattr(message, "tool_calls") and message.tool_calls:
                    for tool_call in message.tool_calls:
                        tool_name = tool_call["name"]
                        tool_args = tool_call["args"]
                        status_box.write(f"🛠️ **Researcher** requested `{tool_name}`")
                        with status_box.expander(f"Tool Input: {tool_name}"):
                            st.json(tool_args)
                else:
                    final_answer = message.content

            elif "tools" in event:
                tool_messages = event["tools"]["messages"]
                for tool_msg in tool_messages:
                    tool_name = tool_msg.name
                    content = tool_msg.content
                    display_res = content[:1000] + "\n...[truncated]" if len(content) > 1000 else content
                    
                    status_box.write(f"⚙️ **Tools** finished `{tool_name}`")
                    with status_box.expander(f"Tool Output: {tool_name}"):
                        st.text(display_res)

            elif "critic" in event:
                messages = event["critic"].get("messages")
                
                if messages and isinstance(messages[-1], HumanMessage):
                    feedback = messages[-1].content.replace("CRITIC FEEDBACK: ", "")
                    status_box.write("🚨 **Critic** rejected the draft. Sending back to Researcher...")
                    with status_box.expander("Critic's Feedback"):
                        st.warning(feedback)
                else:
                    status_box.write("✅ **Critic** approved the final draft!")
        status_box.update(label="Graph execution completed!", state="complete", expanded=False)

        if not final_answer and len(st.session_state.messages) > 0:
            final_answer = "Process completed."

        st.markdown(final_answer)
        st.session_state.messages.append({"role": "assistant", "content": final_answer})