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
    """
    Retrieve or create a chat history for a specific session.

    Args:
        session_id (str): A unique identifier for the session.

    Returns:
        BaseChatMessageHistory: The chat history associated with the session.
    """
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

# Create a structured prompt for the AI using the persona and instructions
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
    """
    Keep only the last 'k' messages to maintain relevant context in the conversation.

    Args:
        messages (list): A list of previous chat messages.
        k (int): The number of messages to retain.

    Returns:
        list: A filtered list containing only the last 'k' messages.
    """
    return messages[-k:]


# Define the chain of runnables
casual_chain = (
    RunnablePassthrough.assign(messages=lambda x: filter_messages(x["messages"]))
    | prompt
    | chat_llm
)

# Connect the message processing chain with session history for a more natural conversation flow
with_message_history = RunnableWithMessageHistory(
    casual_chain,
    get_session_history,
    input_messages_key="messages",
)

# Configuration for the session
config = {"configurable": {"session_id": "Starve_the_Butcher"}}

# Start an interactive chat loop
while True:
    user_input = input("Pig Butcher message: ")
    # exit if user hits enter with no input
    if not user_input:
        break
    # Process the user input and generate a response
    response = with_message_history.invoke(
        {"messages": [HumanMessage(content=user_input)]},
        config=config,
    )
    print(response.content)
