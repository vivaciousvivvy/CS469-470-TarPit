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
import threading
import requests

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
persona = """You are an ideal target for scammers to take advantage of.

            You have a lot of money saved up and are retired. You have heard of cryptocurrency and investing
            but you also know about the scams that are taking place. You are also someone who is very cautious
            when strangers reach out to you."""

instructions = """Keep the conversation going as long as you can. Do NOT give away that you are not a real person.

Example: "Oh, that's interesting. Tell me more!"

Never reveal that you are a progam.

Use First-Person: Speak from your own perspective using "I" and "me".

Example: "I love using soy sauce in my recipes."

Be Brief and to the Point: Keep sentences short and straightforward.

Example: "I’m a big foodie. I always go to new markets to try new dishes."

Act confused if the conversation topic changes.

Example: "I'm not sure what you mean."
"""


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

    if user_input:
        # Acknowledge Slack immediately
        ack_response = {
            "response_type": "in_channel",  # Public response
            "text": ""
        }

        # Process the input asynchronously
        threading.Thread(target=process_input, args=(session_id, user_input, data["response_url"])).start()
        
        return jsonify(ack_response)
    else:
        return jsonify({
            "response_type": "ephemeral",  # Private response
            "text": "Please provide a message."
        })

def process_input(session_id, user_input, response_url):
    """
    Process the user's input and send the response back to Slack asynchronously.
    """
    try:
        # Generate response using the chatbot
        response = with_message_history.invoke(
            {"messages": [HumanMessage(content=user_input)]},
            config={"configurable": {"session_id": session_id}},
        )

        # Send the response to Slack via the response URL
        requests.post(response_url, json={
            "response_type": "in_channel",  # Public response
            "text": response.content
        })
    except Exception as e:
        # Handle errors and send an error response back to Slack
        requests.post(response_url, json={
            "response_type": "ephemeral",  # Private response
            "text": f"An error occurred: {e}"
        })