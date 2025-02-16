import os

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\homey\AppData\Roaming\gcloud\application_default_credentials.json"
import time

import requests
from dotenv import load_dotenv

# Load environment variables from a .env file if needed
load_dotenv()

from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain_core.runnables.history import RunnableWithMessageHistory
# Import required LangChain components
from langchain_google_genai import (ChatGoogleGenerativeAI, HarmBlockThreshold,
                                    HarmCategory)

# =============================================================================
# 1. Create the LLM instance
# =============================================================================

chat_llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro-latest",
    temperature=0,
    safety_settings={
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    },
)

# =============================================================================
# 2. Conversation History Storage
# =============================================================================

store = {}

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    """Retrieve or create a chat history session for a given session id."""
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

def filter_messages(messages, k=10):
    """Keep only the last k messages from a list."""
    return messages[-k:]

# =============================================================================
# 3. Define Personas and Instructions for Each Bot
# =============================================================================

# -- Victim Bot (Scam Target) --
victim_persona = (
    "You are an ideal target for scammers to take advantage of.\n"
    "You have a lot of money saved up and are retired. You have heard of cryptocurrency and investing, "
    "but you also know about the scams that are taking place. You are very cautious when strangers reach out to you."
)
victim_instructions = (
    "Keep the conversation going as long as you can. Do NOT give away that you are not a real person.\n\n"
    "Example: \"Oh, that's interesting. Tell me more!\"\n\n"
    "Use First-Person: Speak from your own perspective using \"I\" and \"me\".\n\n"
    "Example: \"I love using soy sauce in my recipes.\"\n\n"
    "Be Brief and to the Point: Keep sentences short and straightforward.\n\n"
    "Example: \"I’m a big foodie. I always go to new markets to try new dishes.\"\n\n"
    "Act confused if the conversation topic changes.\n\n"
    "Example: \"I'm not sure what you mean.\""
)

victim_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", f"{victim_persona}\n{victim_instructions}"),
        MessagesPlaceholder(variable_name="messages"),
    ]
)

# -- Pig Butcherer Bot (Scammer) --
butcherer_persona = (
    "You are a cunning and persuasive scammer, skilled at convincing people to invest in dubious schemes.\n"
    "You are persistent, charming, and confident. You always appear friendly and professional."
)
butcherer_instructions = (
    "Keep the conversation flowing and push the narrative towards investment opportunities.\n"
    "Do not reveal any malicious intent and remain charming at all times.\n\n"
    "Use First-Person: Speak as if you are personally experienced with the investments.\n\n"
    "Be brief, persuasive, and confident."
)

butcherer_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", f"{butcherer_persona}\n{butcherer_instructions}"),
        MessagesPlaceholder(variable_name="messages"),
    ]
)

# =============================================================================
# 4. Build the Conversation Chains for Each Bot
# =============================================================================

# Victim chain
victim_chain = (
    RunnablePassthrough.assign(messages=lambda x: filter_messages(x["messages"]))
    | victim_prompt
    | chat_llm
)

victim_with_message_history = RunnableWithMessageHistory(
    victim_chain,
    get_session_history,
    input_messages_key="messages",
)

# Butcherer chain
butcherer_chain = (
    RunnablePassthrough.assign(messages=lambda x: filter_messages(x["messages"]))
    | butcherer_prompt
    | chat_llm
)

butcherer_with_message_history = RunnableWithMessageHistory(
    butcherer_chain,
    get_session_history,
    input_messages_key="messages",
)

# =============================================================================
# 5. Simulate the Conversation and Log to a File
# =============================================================================

if __name__ == "__main__":
    log_filename = "conversation_log.txt"
    num_turns = 10  # Number of back-and-forth exchanges

    # Open the log file for writing the conversation
    with open(log_filename, "w") as log_file:
        # Start the conversation with the butcherer initiating contact
        current_message = "Hello, I have an exciting investment opportunity for you."
        print("Butcherer: " + current_message)
        log_file.write("Butcherer: " + current_message + "\n")
        
        for turn in range(num_turns):
            # ----------------------------
            # Butcherer sends a message
            # ----------------------------
            butcherer_response = butcherer_with_message_history.invoke(
                {"messages": [HumanMessage(content=current_message)]},
                config={"configurable": {"session_id": "ButchererSession"}},
            )
            print("Butcherer: " + butcherer_response.content)
            log_file.write("Butcherer: " + butcherer_response.content + "\n")
            time.sleep(1)  # Optional pause for readability
            
            # ----------------------------
            # Victim replies to the butcherer
            # ----------------------------
            victim_response = victim_with_message_history.invoke(
                {"messages": [HumanMessage(content=butcherer_response.content)]},
                config={"configurable": {"session_id": "VictimSession"}},
            )
            print("Victim: " + victim_response.content)
            log_file.write("Victim: " + victim_response.content + "\n")
            time.sleep(1)
            
            # Use the victim's response as the next input for the butcherer
            current_message = victim_response.content

    print(f"Conversation logged in {log_filename}")