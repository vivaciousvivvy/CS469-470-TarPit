import aiohttp
import asyncio
from werkzeug.wrappers import Response
from quart import Quart, request, jsonify
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

# Quart app
app = Quart(__name__)

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
def get_session_history(session_id: str) -> ChatMessageHistory:
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

async def process_input(session_id, user_input, response_url):
    """
    Process the user's input asynchronously and send the response to Slack.
    """
    try:
        # Generate response using the chatbot
        response = with_message_history.invoke(
            {"messages": [HumanMessage(content=user_input)]},
            config={"configurable": {"session_id": session_id}},
        )

        async with aiohttp.ClientSession() as session:
            async with session.post(response_url, json={
                "response_type": "in_channel",  # Public response
                "text": response.content
            }) as resp:
                if resp.status != 200:
                    print(f"Failed to send response: {resp.status} {await resp.text()}")
    except Exception as e:
        async with aiohttp.ClientSession() as session:
            await session.post(response_url, json={
                "response_type": "ephemeral",  # Private response
                "text": f"An error occurred: {e}"
            })

@app.route('/', methods=['POST'])
async def slack_command():
    """
    Entry point for Slack slash commands.
    """
    try:
        # Parse Slack's request
        form = await request.form
        session_id = form.get('user_id')  # Use user ID for session history
        user_input = form.get('text', '')  # Get the user's input text
        response_url = form.get('response_url')  # Slack's response URL

        if user_input:
            # Acknowledge Slack immediately
            ack_response = {
                "response_type": "in_channel",  # Visible to everyone in the channel
                "text": "Processing your request... Please wait."
            }

            # Schedule asynchronous task
            asyncio.create_task(process_input(session_id, user_input, response_url))

            return jsonify(ack_response)
        else:
            return jsonify({
                "response_type": "ephemeral",
                "text": "Please provide a message."
            })
    except Exception as e:
        return jsonify({
            "response_type": "ephemeral",
            "text": f"An error occurred: {e}"
        }), 500

# Google Cloud Function entry point
import asyncio
from werkzeug.wrappers import Response

def respond_to_butcher(request):
    """
    Google Cloud Function entry point for Quart.
    """
    # Function to handle the asynchronous request
    async def handle_request():
        headers = {key: value for key, value in request.headers.items()}

        # Use Google Cloud Functions' `request.data` instead of `await request.get_data()`
        with app.test_request_context(
            path=request.path,
            base_url=request.base_url,
            query_string=request.query_string,
            method=request.method,
            headers=headers,
            data=request.data  # Directly pass the `bytes` object
        ):
            response = await app.full_dispatch_request()
            return response

    # Check if there's an existing event loop
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # Create a new event loop if none exists
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Run the async handler in the event loop
    response = loop.run_until_complete(handle_request())

    # Convert Quart's response to a Werkzeug response
    return Response(response.get_data(), status=response.status_code, headers=dict(response.headers))