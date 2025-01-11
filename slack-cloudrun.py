from flask import Flask, request, jsonify
from langchain_google_genai import ChatGoogleGenerativeAI, HarmCategory, HarmBlockThreshold
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnablePassthrough

app = Flask(__name__)

# Create the LLM
chat_llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro-latest",
    temperature=0,
    safety_settings={
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }
)

# Simple store for conversation history
store = {}

# Allows for multiple sessions and fetches the session history
def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

# Create persona and the prompts
persona = """Fill me in."""
instructions = """Fill me in."""

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            f"""{persona}
            {instructions}
            """,
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)

# Truncate message history to the last k messages
def filter_messages(messages, k=10):
    """Filter the last k messages from the list of messages."""
    return messages[-k:]

# Define the chain of runnables
casual_chain = (
    RunnablePassthrough.assign(messages=lambda x: filter_messages(x["messages"]))
    | prompt
    | chat_llm
)

# Create the runnable with message history
with_message_history = RunnableWithMessageHistory(
    casual_chain,
    get_session_history,
    input_messages_key="messages",
)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    session_id = data.get("session_id", "default")
    user_input = data.get("message")
    
    if not user_input:
        return jsonify({"error": "No message provided"}), 400
    
    config = {"configurable": {"session_id": session_id}}
    response = with_message_history.invoke(
        {"messages": [HumanMessage(content=user_input)]},
        config=config,
    )
    return jsonify({"response": response.content})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)