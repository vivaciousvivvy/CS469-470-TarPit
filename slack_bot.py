import os
import requests
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

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
from slack_bolt.adapter.flask import SlackRequestHandler
from slack_bolt import App




# Set Slack API credentials
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
# Initialize Slack WebClient with the bot token
client = WebClient(token=SLACK_BOT_TOKEN)


SLACK_SIGNING_SECRET = os.environ["SLACK_SIGNING_SECRET"]
verifier = SignatureVerifier(SLACK_SIGNING_SECRET)
SLACK_BOT_USER_ID = os.environ["SLACK_BOT_USER_ID"]


# Initialize the Slack app
app = App(token=SLACK_BOT_TOKEN)

# Initialize the Flask app
flask_app = Flask(__name__)
handler = SlackRequestHandler(app)

# %%
def get_bot_user_id():
    """
    Get the bot user ID using the Slack API.
    Returns:
        str: The bot user ID.
    """
    try:
        # Initialize the Slack client with your bot token
        slack_client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
        response = slack_client.auth_test()
        return response["user_id"]
    except SlackApiError as e:
        print(f"Error: {e}")


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

# Slack Message Handler
@app.event("message")
def handle_message_event(body, say):
    try:
        user = body["event"]["user"]
        text = body["event"]["text"]
    except KeyError:
        say("Sorry, I couldn't process your message.")
        return
    session_id = user

    response = with_message_history.invoke(
        {"messages": [HumanMessage(content=text)]},
        config={"configurable": {"session_id": session_id}},
    )

    say(response.content)


# Flask route for Slack events
@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

if __name__ == "__main__":
    flask_app.run(host="0.0.0.0", port=8080)

# %%
