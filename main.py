import firebase_admin
from firebase_admin import credentials, auth, firestore
from flask import Flask, request, jsonify

# Initialize Flask app
app = Flask(__name__)

# Initialize Firebase Admin SDK
cred = credentials.Certificate('firebase_config.json')
firebase_admin.initialize_app(cred)

# Initialize Firestore
db = firestore.client()


@app.route('/')
def index():
    return "Welcome to Portal Gambit!"


@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    try:
        user = auth.create_user(email=email, password=password)
        return jsonify({"message": "User created successfully", "uid": user.uid}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    try:
        user = auth.get_user_by_email(email)
        # Here you would typically verify the password and generate a token
        return jsonify({"message": "User logged in successfully", "uid": user.uid}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/create_game', methods=['POST'])
def create_game():
    data = request.json
    game_data = {
        'player1': data.get('player1'),
        'player2': data.get('player2'),
        'status': 'waiting',
        'moves': []
    }
    try:
        game_ref = db.collection('games').add(game_data)
        return jsonify({"message": "Game created successfully", "game_id": game_ref[1].id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


if __name__ == '__main__':
    app.run(debug=True)
