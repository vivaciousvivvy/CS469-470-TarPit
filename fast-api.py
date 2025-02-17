from fastapi import FastAPI, HTTPException, Depends, Request
from pydantic import BaseModel
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
import httpx
import asyncio
import uvicorn

# Load environment variables
load_dotenv()

app = FastAPI()

# Create the LLM
def get_llm():
    """Create and return an AI chat model with specific settings."""
    return ChatGoogleGenerativeAI(
        model="gemini-1.5-pro-latest",
        temperature=1,
        safety_settings={
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        },
    )

# Simple store for conversation history
store = {}

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    """Get or create session history to keep track of user conversations."""
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

# Persona and instructions
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

Example: "I'm not sure what you mean."""

def get_prompt(persona: str, instructions: str):
    """Create a structured prompt using persona and instructions."""
    return ChatPromptTemplate.from_messages(
        [
            ("system", f"""{persona}
                {instructions}
            """),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )

def filter_messages(messages, k=10):
    """Filter the last k messages from the list of messages."""
    return messages[-k:]

def get_casual_chain():
    """Create and return a casual chat chain."""
    return (
        RunnablePassthrough.assign(messages=lambda x: filter_messages(x["messages"]))
        | get_prompt(persona, instructions)
        | get_llm()
    )

def get_with_message_history():
    """Connect the message processing chain with session history for a more natural conversation flow."""
    return RunnableWithMessageHistory(
        get_casual_chain(),
        get_session_history,
        input_messages_key="messages",
    )

# Chatwoot API Credentials


@app.post("/chatwoot-webhook")
async def chatwoot_webhook(request: Request, with_message_history=Depends(get_with_message_history)):
    """Handle incoming messages from Chatwoot, process them with the AI model, and return a response.

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
        response_text = await asyncio.to_thread(
            with_message_history.invoke,
            {"messages": [HumanMessage(content=message_content)]},
            config=config,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # asyncio.create_task(send_response_to_chatwoot(conversation_id, response_text.content))

    return {"status": response_text}

async def send_response_to_chatwoot(conversation_id: int, response_text: str):
    """Send a message back to Chatwoot in the same conversation."""

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
    """Start the FastAPI server using Uvicorn."""
    uvicorn.run(app, host="0.0.0.0", port=8000)