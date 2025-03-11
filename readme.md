# Pig Butchering Scammer Chatbot Project

## Summary about the project

## What is Chatwoot?
- Chatwoot is an open-source engagement platform that helps manage conversations across different messaging channels like Messengers, SMS, Instagram. It provides a unified inbox for users to interact with with others efficiently.

## What is the fastAPI.py does?
- This FastAPI application is designed to process chatbot conversations through Chatwoot. It uses Google Gemini AI to generate responses based on user messages. This file aslo maintains conversation history and follows a specific persona when replying to messages.

## What is the discord.py file does?
- The 'discord.py' file is used to create a pig bitchering bot that interacts with scammers through Discord channels.

### discord.py File Behavior
- The Discord bot runs using the 'bot.run()' function, which connects the bot to the Discord API using the provided bot token. Once the bot is running, it listens for events and commands like 'ping', '!echo', and '!butcher'. When a scammer triggers a command, the bot processes the request, interacts with the AI model, and sends the response back to the user in the Discord channel.

- To start the bot, you simply run the Python script containing this code, and the bot will be online and responsive to scammer interactions.


venv commands:

Start:
virtualenv -p python3 env
source env/bin/activate
pip install -r requirements.txt

Leave:
deactivate
