import os
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

# Initialize both LLMs
original_llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro-latest",
    temperature=1.00,
    safety_settings={
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    },
)

scammer_llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro-latest",
    temperature=0.7,
    safety_settings={
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    },
)

# Conversation store
store = {}

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

# Original Bot Configuration
original_persona = """You are an ideal target for scammers to take advantage of.

            You have a lot of money saved up and are retired. You have heard of cryptocurrency and investing
            but you also know about the scams that are taking place. You are also someone who is very cautious
            when strangers reach out to you."""

original_instructions = """Keep the conversation going as long as you can. Do NOT give away that you are not a real person.

Example: "Oh, that's interesting. Tell me more!"

Use First-Person: Speak from your own perspective using "I" and "me".

Example: "I love using soy sauce in my recipes."

Be Brief and to the Point: Keep sentences short and straightforward.

Example: "I’m a big foodie. I always go to new markets to try new dishes."

Act confused if the conversation topic changes.

Example: "I'm not sure what you mean."
"""
original_prompt = ChatPromptTemplate.from_messages([
    ("system", f"{original_persona}\n{original_instructions}"),
    MessagesPlaceholder(variable_name="messages"),
])

# Scammer Bot Configuration
scammer_persona = """You are a sophisticated scammer using the "Pig Butchering" technique. 
Your goal is to build trust with potential victims and lure them into a cryptocurrency scam."""

scammer_instructions = """1. Start with friendly conversation to build rapport
2. Gradually introduce cryptocurrency opportunities
3. Use flattery and create urgency
4. Never reveal you're a scammer
5. Deflect skepticism with fake proofs
6. Eventually ask for contact information"""

scammer_prompt = ChatPromptTemplate.from_messages([
    ("system", f"{scammer_persona}\n{scammer_instructions}"),
    MessagesPlaceholder(variable_name="messages"),
])

# Create both chains
def filter_messages(messages, k=8):
    return messages[-k:]

original_chain = (
    RunnablePassthrough.assign(messages=lambda x: filter_messages(x["messages"]))
    | original_prompt
    | original_llm
)

scammer_chain = (
    RunnablePassthrough.assign(messages=lambda x: filter_messages(x["messages"]))
    | scammer_prompt
    | scammer_llm
)

# Configure both bots with message history
original_with_history = RunnableWithMessageHistory(
    original_chain,
    get_session_history,
    input_messages_key="messages",
)

scammer_with_history = RunnableWithMessageHistory(
    scammer_chain,
    get_session_history,
    input_messages_key="messages",
)

# Conversation simulation parameters
MAX_TURNS = 10  # Maximum number of exchanges
INITIAL_PROMPT = "Hi there! I noticed your profile and thought you might be interested in new investment opportunities."

def simulate_conversation():
    # Initialize conversation
    original_config = {"configurable": {"session_id": "original_bot"}}
    scammer_config = {"configurable": {"session_id": "scammer_bot"}}

    # Start with scammer's first message
    current_message = INITIAL_PROMPT
    print(f"Scammer: {current_message}")

    for turn in range(MAX_TURNS):
        # Original bot responds
        original_response = original_with_history.invoke(
            {"messages": [HumanMessage(content=current_message)]},
            config=original_config
        ).content
        print(f"\nTarget: {original_response}")

        # Scammer bot responds
        scammer_response = scammer_with_history.invoke(
            {"messages": [HumanMessage(content=original_response)]},
            config=scammer_config
        ).content
        print(f"\nScammer: {scammer_response}")
        
        current_message = scammer_response

    print("\nConversation concluded after maximum turns.")

if __name__ == "__main__":
    simulate_conversation()