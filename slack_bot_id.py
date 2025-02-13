import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Load environment variables (e.g., SLACK_BOT_TOKEN)
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]

# Initialize Slack client
slack_client = WebClient(token=SLACK_BOT_TOKEN)

# Function to get the Slack Bot User ID dynamically
def get_user_id():
    try:
        # Use the 'auth.test' API to retrieve bot information
        response = slack_client.auth_test()
        return response["user_id"]
    except SlackApiError as e:
        print(f"Error fetching bot user ID: {e.response['error']}")
        raise

# Dynamically fetch the bot user ID
SLACK_BOT_USER_ID = get_user_id()

# Print the bot user ID for verification (optional)
print(f"Slack Bot User ID: {SLACK_BOT_USER_ID}")

# Your existing Slack bot code continues here
