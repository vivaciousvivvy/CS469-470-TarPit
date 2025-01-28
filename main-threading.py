import os
import requests
from flask import Flask, request, jsonify
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

load_dotenv()

# Initialize Flask app (used for testing locally)
app = Flask(__name__)

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


def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]


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


def filter_messages(messages, k=10):
    """Filter the last k messages from the list of messages."""
    return messages[-k:]


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


def process_message(user_input, session_id, response_url):
    try:
        # Perform the actual processing
        response = with_message_history.invoke(
            {"messages": [HumanMessage(content=user_input)]},
            config={"configurable": {"session_id": session_id}},
        )

        # Send the final response back to Slack
        requests.post(
            response_url,
            json={"response_type": "in_channel", "text": response.content}
        )
    except Exception as e:
        # Handle errors and send error messages to Slack
        requests.post(
            response_url,
            json={"response_type": "ephemeral", "text": f"Error processing request: {str(e)}"}
        )

@app.route("/", methods=["POST"])
def respond_to_butcher(request):
    try:
        # Parse Slack request payload
        request_form = request.form
        user_input = request_form.get("text", "")
        response_url = request_form.get("response_url")
        session_id = request_form.get("user_id", "respond_to_butcher")

        if not user_input:
            return jsonify({"response_type": "ephemeral", "text": "No input provided"}), 200

        # Respond immediately to Slack to avoid timeout
        requests.post(
            response_url,
            json={"response_type": "ephemeral", "text": "Processing your request..."}
        )

        # Process the message asynchronously
        from threading import Thread
        Thread(target=process_message, args=(user_input, session_id, response_url)).start()

        # Return an acknowledgment to Slack
        return jsonify({"response_type": "ephemeral", "text": "Your request is being processed."}), 200
    except Exception as e:
        return jsonify({"response_type": "ephemeral", "text": f"Error: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)