from flask import Flask, request, jsonify

# Flask app wrapper for Google Cloud Functions
app = Flask(__name__)

@app.route('/', methods=['POST'])
def hello_command():
    # Parse the request data from Slack
    data = request.form
    user_name = data.get('user_name', 'there')
    
    # Respond with a friendly message
    response = {
        "response_type": "in_channel",  # "in_channel" makes it visible to all, "ephemeral" is private to the user
        "text": f"Hello, {user_name}! 👋 How can I assist you today?"
    }
    
    return jsonify(response)

# Google Cloud Functions entry point
def slack_hello(request):
    return app(request)