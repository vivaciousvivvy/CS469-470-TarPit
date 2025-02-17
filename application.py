from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
app = Flask(__name__)

# Set up the database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
db = SQLAlchemy(app)

# with app.app_context():
#     db.create_all()

class Drink(db.Model):
    """
    Represents a drink with a name and a short description.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(120))

    def __repr__(self):
        """
        Returns a string with drink info.
        """
        return f"({self.name} - {self.description})"

# Create the database tables
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    """
    Root endpoint that returns a simple greeting message.
    """
    return 'Hello!'

@app.route('/drinks')
def get_drinks():
    """
    Retrieve all drinks from the database and return them as JSON.
    """
    drinks = Drink.query.all()
    output = []
    for drink in drinks:
        drink_data = {'name': drink.name, 'description': drink.description}
        output.append(drink_data)

    return {"drinks": output}

@app.route('/drinks/<id>')
def get_drink(id):
    """
    Get a single drink by ID and return it as JSON.
    """
    drink = Drink.query.get_or_404(id)
    return {"name": drink.name, "description": drink.description}

@app.route('/drinks', methods=['POST'])
def add_drink():
    """
    Add a new drink to the database.
    
    Expects JSON data with 'name' and 'description' fields.
    
    Returns:
        dict: A dictionary containing the ID of the newly added drink.
    """
    print(f"Content-Type: {request.headers.get('Content-Type')}")
    drink = Drink(name=request.json['name'], description=request.json['description'])
    db.session.add(drink)
    db.session.commit()
    return {'id': drink.id}

@app.route('/drinks/<id>', methods=['DELETE'])
def delete_drink(id):
    """
    Delete a drink from the database using its ID.
    """
    drink = Drink.query.get(id)
    if drink in None:
        return {"error": "not found"}
    db.session.delete(drink)
    db.session.commit()
    return {"message": "yeet!"}

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)