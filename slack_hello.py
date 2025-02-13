from flask import Flask, request, jsonify

# Flask app definition
app = Flask(__name__)

@app.route('/', methods=['POST'])
def hello_command():
    try:
        # Parse Slack's request
        user_name = request.form.get('user_name', 'there')
        
        # Create a Slack response
        response = {
            "response_type": "in_channel",  # Visible to everyone in the channel
            "text": f"Hello, {user_name}! 👋 How can I assist you today?"
        }
        return jsonify(response)
    except Exception as e:
        # Handle any unexpected errors
        return jsonify({
            "response_type": "ephemeral",  # Visible only to the user who triggered the command
            "text": f"An error occurred: {str(e)}"
        }), 500

# Google Cloud Function entry point
def slack_hello(request):
    # Convert headers to a dictionary to avoid immutability issues
    headers = {key: value for key, value in request.headers.items()}

    # Call Flask app directly
    with app.test_request_context(
        path=request.path,
        base_url=request.base_url,
        query_string=request.query_string,
        method=request.method,
        headers=headers,
        data=request.get_data()
    ):
        return app.full_dispatch_request()