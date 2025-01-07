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
from dotenv import load_dotenv

load_dotenv()

# Intents are required for the bot to work with certain events
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

# Create bot instance
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
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
    await interaction.response.send_message("Pong! 🏓")

@bot.tree.command(name="echo", description="Echo the last message in the current channel")
async def echo(interaction: discord.Interaction):
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
chat_llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro-latest",
    temperature=0,
    safety_settings={
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    },
)

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
bot.run('MTMxNzA0MjQ1MTk4NjUxODAyNg.GUTRiV.FqyBL952n3oonAflBngHY-g6Q3xJ2l_Vhn22fY')
