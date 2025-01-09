import os
import requests
from dotenv import load_dotenv
load_dotenv()

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

from flask import Flask, request, jsonify
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack.signature import SignatureVerifier


app = Flask(__name__)

# Set up Slack client and signature verifier
slack_token = os.getenv("SLACK_BOT_TOKEN")
client = WebClient(token=slack_token)
verifier = SignatureVerifier(os.getenv("SLACK_SIGNING_SECRET"))


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


# Allowws for multiple sessions and fetches the session history
def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]


# # Create persona and the prompts

persona = """You are an ideal target for scammers to take advantage of.

            You have a lot of money saved up and are retired. You have heard of cryptocurrency and investing
            but you also know about the scams that are taking place. You are also someone who is very cautious
            when strangers reach out to you."""

instructions = """Keep the conversation going as long as you can. Do NOT give away that you are not a real person.

Example: "Oh, that's interesting. Tell me more!"

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

config = {"configurable": {"session_id": "Starve_the_Butcher"}}

# Handle Slack events (messages)
@app.route("/slack/events", methods=["POST"])
def slack_events():
    # First, check the challenge parameter from Slack's verification request
    slack_event = request.json
    
    # If it's the challenge request, respond with the challenge value
    if "challenge" in slack_event:
        return jsonify({"challenge": slack_event["challenge"]})

    # Now check the validity of the Slack request
    if not verifier.is_valid_request(request.data, request.headers):
        return "Invalid request", 400

    # Respond to a message event
    if "event" in slack_event:
        event = slack_event["event"]
        user_id = event.get("user")
        text = event.get("text")
        
        if user_id and text:
            # Handle the message (you can call your message handler function here)
            response = handle_message(text, user_id)
            return jsonify(response)

    return "OK", 200


# Function to handle messages and send a response to Slack
def handle_message(user_input, user_id):
    config = {"configurable": {"session_id": user_id}}

    response = with_message_history.invoke(
        {"messages": [HumanMessage(content=user_input)]},
        config=config,
    )

    message_text = response.content
    return send_message_to_slack(message_text, user_id)

# Send message to Slack
def send_message_to_slack(text, user_id):
    try:
        # Send message to Slack channel or user (user_id for direct message)
        client.chat_postMessage(channel=user_id, text=text)
        return {"status": "success"}
    except SlackApiError as e:
        print(f"Error sending message: {e.response['error']}")
        return {"status": "failure", "error": e.response['error']}

# Slack command to trigger the bot
@app.route("/slack/command", methods=["POST"])
def slack_command():
    if not verifier.is_valid_request(request.data, request.headers):
        return "Invalid request", 400

    command_data = request.form
    user_input = command_data.get("text")
    user_id = command_data.get("user_id")

    # Handle the incoming message from the Slack command
    return handle_message(user_input, user_id)

if __name__ == "__main__":
    app.run(port=5000)