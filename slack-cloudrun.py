# [START functions_slack_setup]
import os

from flask import jsonify
import functions_framework
import googleapiclient.discovery
from slack.signature import SignatureVerifier

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


# kgsearch = googleapiclient.discovery.build(
#     "kgsearch", "v1", developerKey=os.environ["KG_API_KEY"], cache_discovery=False
# )

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

config = {"configurable": {"session_id": "Starve_the_Butcher"}}

# [END functions_slack_setup]

# [START functions_verify_webhook]
def verify_signature(request):
    request.get_data()  # Decodes received requests into request.data

    verifier = SignatureVerifier(os.environ["SLACK_SECRET"])

    if not verifier.is_valid_request(request.data, request.headers):
        raise ValueError("Invalid request/credentials.")


# [END functions_verify_webhook]


# [START functions_slack_format]
def format_slack_message(query, response):
    entity = None
    if (
        response
        and response.get("itemListElement") is not None
        and len(response["itemListElement"]) > 0
    ):
        entity = response["itemListElement"][0]["result"]

    message = {
        "response_type": "in_channel",
        "text": f"Query: {query}",
        "attachments": [],
    }

    attachment = {}
    if entity:
        name = entity.get("name", "")
        description = entity.get("description", "")
        detailed_desc = entity.get("detailedDescription", {})
        url = detailed_desc.get("url")
        article = detailed_desc.get("articleBody")
        image_url = entity.get("image", {}).get("contentUrl")

        attachment["color"] = "#3367d6"
        if name and description:
            attachment["title"] = "{}: {}".format(entity["name"], entity["description"])
        elif name:
            attachment["title"] = name
        if url:
            attachment["title_link"] = url
        if article:
            attachment["text"] = article
        if image_url:
            attachment["image_url"] = image_url
    else:
        attachment["text"] = "No results match your query."
    message["attachments"].append(attachment)

    return message


# [END functions_slack_format]


# [START functions_slack_request]
def make_search_request(query):
    req = kgsearch.entities().search(query=query, limit=1)
    res = req.execute()
    return format_slack_message(query, res)


# [END functions_slack_request]


# [START functions_slack_search]
@functions_framework.http
def kg_search(request):
    if request.method != "POST":
        return "Only POST requests are accepted", 405

    verify_signature(request)

    response = with_message_history.invoke(
        {"messages": [HumanMessage(content=request)]},
        config=config,
    )

    return jsonify(response.content)


    # kg_search_response = make_search_request(request.form["text"])
    # return jsonify(kg_search_response)

# [END functions_slack_search]