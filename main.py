import asyncio
import json
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import JSONResponse
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

# FastAPI app
app = FastAPI()

# Create the LLM and configure the AI model that will generate chatbot responses.
"""A Google Generative AI chat model configured for conversational tasks.

Attributes:
    model (str): The model version to use
    temperature (float): Controls randomness in responses
    safety_settings (dict): Configures safety filters for content moderation.
"""
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
    """Gets or creates a chat history for a user.
    
    Args:
        session_id (str): A unique identifier representing a user's session.
    
    Returns:
        BaseChatMessageHistory: The user's chat history for maintaining conversation context.
    """
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



"""A structured prompt template for the AI, combining the persona and instructions.

Attributes:
    persona (str): The personality and background of the AI.
    instructions (str): Guidelines for how the AI should respond.
    MessagesPlaceholder: A placeholder for the chat message history.
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
    """Keeps only the last k messages in memory to maintain relevant context.
    
    Args:
        messages (list): List of previous chat messages.
        k (int): Number of messages to retain.
    
    Returns:
        list: Filtered list containing only the last k messages.
    """
    return messages[-k:]

# Define the chain of runnables
casual_chain = (
    RunnablePassthrough.assign(messages=lambda x: filter_messages(x["messages"]))
    | prompt
    | chat_llm
)

# Create the runnable with message history
"""A runnable chain that maintains conversation history for each session.

Attributes:
    casual_chain: The chain of runnables for processing messages.
    get_session_history: Function to retrieve or create session-specific chat history.
    input_messages_key (str): The key for accessing messages in the input.
"""
with_message_history = RunnableWithMessageHistory(
    casual_chain,
    get_session_history,
    input_messages_key="messages",
)

class MessageRequest(BaseModel):
    """Represents a user message request with a session ID and message content.
    
    Attributes:
        session_id (str): The unique ID for the chat session.
        message (str): The message sent by the user.
    """
    session_id: str
    message: str

@app.post("/chat/")
async def chat(request: MessageRequest):
    """API endpoint for chatbot interaction. 
    It receives user messages and returns chatbot responses.
    
    Args:
        request (MessageRequest): The request object containing session ID and user message.
    
    Returns:
        dict: A dictionary containing the AI-generated response.
    """
    try:
        config = {"configurable": {"session_id": request.session_id}}
        response = with_message_history.invoke(
            {"messages": [HumanMessage(content=request.message)]},
            config=config,
        )
        return {"response": response.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    


# Chatwoot API Credentials


@app.post("/chatwoot-webhook")
async def chatwoot_webhook(request: Request):
    """Receive messages from Chatwoot, process them using the AI model, and return a response.

    Args:
        request (Request): The HTTP request object.

    Returns:
        dict: A dictionary containing the status of the response.
    """
    data = await request.json()
    print(f"Received Webhook: {data}")
    # Extract message details
    conversation_id = data["id"]
    message_content = data["messages"][0]["content"]

    try:
        config = {"configurable": {"session_id": conversation_id}}
        response_text = with_message_history.invoke(
            {"messages": [HumanMessage(content=message_content)]},
            config=config,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    asyncio.create_task(send_response_to_chatwoot(conversation_id, response_text.content))

    return {"status": "success"}

def process_message(message: str) -> str:
    """Modify or process the message as needed.
    Here, we're just echoing back with a prefix.

    Args:
        message (str): The incoming message to be processed.

    Returns:
        str: The processed message with a prefix added.
    """
    return f"Echo: {message}"

# Replace with your actual Chatwoot API key
CHATWOOT_API_KEY = "<FMI>" 

async def send_response_to_chatwoot(conversation_id: int, response_text: str):
    """Send a response message back to a Chatwoot conversation.

    Args:
        conversation_id (int): The ID of the Chatwoot conversation where the response will be sent.
        response_text (str): The text of the response to be sent.

    Returns:
        None: This function does not return anything but prints the HTTP response status and text.
    """

    url = ""
    headers = {
        "Content-Type": "application/json",
        "api_access_token": CHATWOOT_API_KEY
    }
    payload = {
        "content": response_text,
        "message_type": "outgoing",
        "private": False  # Set to True if you want it to be internal
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        print(f"Response sent: {response.status_code}, {response.text}")

if __name__ == "__main__":
    """
    Start the FastAPI server using Uvicorn.

    Args:
        None

    Returns:
        None: This block starts the server and keeps it running.
    """
    uvicorn.run(app, host="0.0.0.0", port=8000)