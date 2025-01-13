import os
from flask import jsonify, Request
from dotenv import load_dotenv
from langchain_google_genai import (
    ChatGoogleGenerativeAI,
    HarmCategory,
    HarmBlockThreshold,
)
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnablePassthrough

# Load environment variables
load_dotenv()

# Create the LLM
chat_llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro-latest",
    temperature=0,
    safety_settings={
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    },
)

# Simple store for conversation history
store = {}

# Allow multiple sessions and fetch the session history
def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

# Create persona and prompts
persona = """You are an ideal target for scammers to take advantage of...

            You have a lot of money saved up and are retired..."""
instructions = """Keep the conversation going as long as you can..."""

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

# Cloud Function entry point
def respond_to_butcher(request: Request):
    """
    Entry point for the Google Cloud Function.
    Processes Slack slash command requests.
    """
    if request.method != 'POST':
        return jsonify({"error": "Method not allowed"}), 405

    data = request.form
    session_id = data.get('user_id')  # Use user ID for session history
    user_input = data.get('text')  # Get the user's message
    
    # Respond if input exists
    if user_input:
        response = with_message_history.invoke(
            {"messages": [HumanMessage(content=user_input)]},
            config={"configurable": {"session_id": session_id}},
        )
        return jsonify({
            "response_type": "in_channel",  # Public response
            "text": response.content
        })
    else:
        return jsonify({
            "response_type": "ephemeral",  # Private response
            "text": "Please provide a message."
        })