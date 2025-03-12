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
from profile_generator import firestore_storage_manager, profile_generator

# Load environment variables
load_dotenv()

app = FastAPI()
generator = profile_generator.ProfileGenerator()
db = firestore_storage_manager.PeopleDatabase()

# Create the LLM
def get_llm():
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
    return (
        RunnablePassthrough.assign(messages=lambda x: filter_messages(x["messages"]))
        | get_prompt(persona, instructions)
        | get_llm()
    )

def get_with_message_history():
    return RunnableWithMessageHistory(
        get_casual_chain(),
        get_session_history,
        input_messages_key="messages",
    )

# Chatwoot API Credentials


@app.post("/chatwoot-webhook")
async def chatwoot_webhook(request: Request):
    data = await request.json()
    print(f"Received Webhook: {data}")

    # Extract conversation details
    conversation_id = str(data["id"])  # Ensure ID is a string
    message_content = data["messages"][0]["content"]

    if db.get_person(conversation_id) is None:
        name = generator.generate_name()
        bio = generator.generate_bio(name)
        old_id = db.add_person(name, bio, "test", "test")
        db.change_victim_id(old_id, conversation_id)

    try:
        # Retrieve conversation history from Firestore
        conversation_history = db.get_conversation_history(conversation_id)

        # Ensure messages are formatted as BaseMessages
        formatted_history = [
            HumanMessage(content=msg["text"]) for msg in conversation_history
        ]

        # Add the new message to the conversation
        messages = formatted_history + [HumanMessage(content=message_content)]

        # Generate response using LLM
        config = {"configurable": {"session_id": conversation_id}}
        response_text = await asyncio.to_thread(
            get_llm().invoke,
            messages,  # Pass as a list, not a dictionary
            config=config,
        )

        # Store new message in Firestore
        db.add_message_to_conversation(
            conversation_id, {"speaker": "victim", "text": message_content}
        )
        db.add_message_to_conversation(
            conversation_id, {"speaker": "butcher", "text": response_text.content}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": response_text.content}

    # asyncio.create_task(send_response_to_chatwoot(conversation_id, response_text.content))

async def send_response_to_chatwoot(conversation_id: int, response_text: str):
    """
    Send a message back to Chatwoot in the same conversation.
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
    uvicorn.run(app, host="0.0.0.0", port=8000)