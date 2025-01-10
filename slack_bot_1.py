import os
from flask import Flask, request, jsonify
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack.signature import SignatureVerifier
from langchain_google_genai import (
    ChatGoogleGenerativeAI,
    HarmCategory,
    HarmBlockThreshold,
)
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.runnables import RunnablePassthrough

# Environment variables
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")

# Initialize Slack client and signature verifier
client = WebClient(token=SLACK_BOT_TOKEN)
verifier = SignatureVerifier(SLACK_SIGNING_SECRET)

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

# Fetches session history
def get_session_history(session_id: str):
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

# Filter last k messages
def filter_messages(messages, k=10):
    """Filter the last k messages from the list of messages."""
    return messages[-k:]

# Define chain of runnables
casual_chain = (
    RunnablePassthrough.assign(messages=lambda x: filter_messages(x["messages"]))
    | prompt
    | chat_llm
)

with_message_history = RunnableWithMessageHistory(
    casual_chain,
    get_session_history,
    input_messages_key="messages",
)

config = {"configurable": {"session_id": "Starve_the_Butcher"}}

# Slack command handler
def slack_handler(request):
    # Verify Slack request
    slack_signature = request.headers.get("X-Slack-Signature", "")
    slack_timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    if not verifier.is_valid_request(request.get_data(), slack_signature, slack_timestamp):
        return jsonify({"error": "Invalid request signature"}), 403

    # Parse incoming Slack request
    data = request.form
    if data.get("command") == "/startchat":
        user_id = data.get("user_id")
        session_id = user_id

        # Start a conversation with the persona
        response = with_message_history.invoke(
            {"messages": [HumanMessage(content="Start a chat")]},
            config={"configurable": {"session_id": session_id}},
        )

        # Respond to the user
        return jsonify({
            "response_type": "in_channel",  # Public response in the channel
            "text": response.content,
        })

    elif data.get("command") == "/reply":
        user_id = data.get("user_id")
        text = data.get("text")
        session_id = user_id

        # Continue conversation based on user input
        response = with_message_history.invoke(
            {"messages": [HumanMessage(content=text)]},
            config={"configurable": {"session_id": session_id}},
        )

        # Respond to the user
        return jsonify({
            "response_type": "in_channel",
            "text": response.content,
        })

    return jsonify({"text": "Unknown command"}), 400


# Google Cloud Function entry point
def slack_bot(request):
    # Process incoming HTTP request
    if request.method == "POST":
        return slack_handler(request)
    return jsonify({"error": "Invalid request method"}), 405
