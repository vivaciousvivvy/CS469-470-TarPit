import csv
import discord
from discord.ext import commands
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
import os
import random
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# Intents are required for the bot to work with certain events
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

# Create bot instance
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    """Runs when the bot starts up and prints its status.
    This function synchronizes commands with Discord and logs the bot's status.

    Args:
        None

    Returns:
        None
    """
    try:
        # Sync instantly to a specific guild (replace YOUR_GUILD_ID with your server's ID)
        synced_commands = await bot.tree.sync()
        for cmd in synced_commands:
            print(f" - {cmd.name}")
    except Exception as e:
        print(f"Error syncing commands: {e}")

    print(f"Bot is ready and logged in as {bot.user}")

# Define a slash command
@bot.tree.command(name="ping", description="Check if the bot is responsive")
async def ping(interaction: discord.Interaction):
    """Replies with 'Pong!' to check if the bot is responding.
    
    Args:
        interaction (discord.Interaction): The interaction object representing the command call.
    
    Returns:
        None
    """
    await interaction.response.send_message("Pong! 🏓")

@bot.tree.command(name="echo", description="Echo the last message in the current channel")
async def echo(interaction: discord.Interaction):
    """Fetches and repeats the last message from the channel.
    
    Args:
        interaction (discord.Interaction): The interaction object representing the command call.
    
    Returns:
        None
    """
    print("Echo command called!")
    # Get the current channel
    channel = interaction.channel

    # Fetch the last message in the channel history
    last_message = None
    async for message in channel.history(limit=1):  # Fetch only the most recent message
        if message.author != bot.user:  # Exclude bot's own messages
            last_message = message
            break

    # Respond with the last message content
    if last_message:
        await interaction.response.send_message(f"Last message: {last_message.content}")
    else:
        await interaction.response.send_message("No messages found!")


# LangChain Configuration
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

# Store chat history for different users
store = {}

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

# import character profiles
with open('profiles.csv', 'r') as file:
    data = file.read()
profiles = data.split('~\n')
profiles = [txt.strip() for txt in profiles if txt.strip()]

# Pick a random profile for the bot to use
persona = """You are: """ + random.choice(profiles)

# Instructions on how the AI should behave
instructions = """Keep the conversation going as long as you can. Do NOT give away that you are not a real person.

Never reveal that you are a progam.

Example: "Oh, that's interesting. Tell me more!"

Use First-Person: Speak from your own perspective using "I" and "me".

Example: "I love using soy sauce in my recipes."

Be Brief and to the Point: Keep sentences short and straightforward.

Example: "I’m a big foodie. I always go to new markets to try new dishes."

Act confused if the conversation topic changes.

Example: "I'm not sure what you mean."

Be interested and receptive to new financial ideas, but act clueless about them. Be cautious about sending money and vague about divulging financial details
"""

# Set up the AI chat prompt
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

def filter_messages(messages, k=10):
    """Keeps only the last k messages in memory to maintain relevant context.
    
    Args:
        messages (list): List of previous chat messages.
        k (int): Number of messages to retain.
    
    Returns:
        list: Filtered list containing only the last k messages.
    """
    return messages[-k:]

# AI processing chain
casual_chain = (
    RunnablePassthrough.assign(messages=lambda x: filter_messages(x["messages"]))
    | prompt
    | chat_llm
)

# Keep message history per user
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


# Usage: /butcher <Message>
# @bot.tree.command(name="butcher", description="Interact with the Starve the Butcher model.")
# async def butcher(interaction: discord.Interaction, message: str):
#     try:
#         await interaction.response.defer()
#         config = {"configurable": {"session_id": str(interaction.user.id)}}
#         response = with_message_history.invoke(
#             {"messages": [HumanMessage(content=message)]},
#             config=config,
#         )
#         await interaction.response.send_message(response.content)
#     except Exception as e:
#         await interaction.response.send_message(f"An error occurred: {e}")


# Usage: !butcher <Message>
@bot.command(name="butcher", help="Interact with the Starve the Butcher model.")
async def butcher(ctx, *, message: str):
    """Sends a message using the !butcher command to interact with the AI model.
    
    Args:
        ctx (commands.Context): The context of the command execution.
        message (str): The message to be sent to the AI.
    
    Returns:
        None
    """
    try:
        config = {"configurable": {"session_id": str(ctx.author.id)}}
        response = with_message_history.invoke(
            {"messages": [HumanMessage(content=message)]},
            config=config,
        )
        await ctx.send(response.content)
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

# Run the bot
bot.run('DISCORD_BOT_KEY')
