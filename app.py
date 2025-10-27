from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

# MongoDB Atlas Configuration
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb+srv://web_vul:web_vul@team20.znx7o.mongodb.net/')
DB_NAME = "retro_games_db"

# Initialize MongoDB client
try:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    users_collection = db['users']
    games_collection = db['user_games']
    
    # Create unique index on username and email
    users_collection.create_index([('username', 1)], unique=True)
    users_collection.create_index([('email', 1)], unique=True)
    
    print("✅ Successfully connected to MongoDB Atlas")
except Exception as e:
    print(f"❌ Error connecting to MongoDB: {e}")

# Sample game data
GAMES = [
    {
        'name': 'Super Mario Bros',
        'file': 'roms/SuperMarioBros.nes',
        'thumbnail': 'assets/super-mario-bros.png'
    },
    {
        'name': 'Sonic Hedgehog', 
        'file': 'roms/SonicTheHedgehog.md',
        'thumbnail': 'assets/sonic-hedgehog.png'
    },
    {
        'name': 'Tetris',
        'file': 'roms/Tetris.nes', 
        'thumbnail': 'assets/tetris.png'
    }
]

@app.route('/')
def index():
    return render_template('index.html', games=GAMES)

@app.route('/play')
def play_game():
    # Get game parameters from URL
    game_name = request.args.get('game', '')
    game_file = request.args.get('file', '')
    
    return render_template('game_player.html', 
                         game_name=game_name, 
                         game_file=game_file)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember')
        
        # Find user by username or email
        user = users_collection.find_one({
            '$or': [
                {'username': username},
                {'email': username}
            ]
        })
        
        if user and check_password_hash(user['password'], password):
            # Login successful
            session['user_id'] = str(user['_id'])
            session['username'] = user['username']
            
            if remember:
                session.permanent = True
                app.permanent_session_lifetime = timedelta(days=30)
            
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username/email or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validation
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('register.html')
        
        try:
            # Create new user
            hashed_password = generate_password_hash(password)
            
            user_data = {
                'username': username,
                'email': email,
                'password': hashed_password,
                'created_at': datetime.utcnow(),
                'last_login': datetime.utcnow(),
                'game_progress': [],
                'favorite_games': []
            }
            
            result = users_collection.insert_one(user_data)
            
            # Auto-login after registration
            session['user_id'] = str(result.inserted_id)
            session['username'] = username
            
            flash('Account created successfully!', 'success')
            return redirect(url_for('index'))
            
        except DuplicateKeyError:
            flash('Username or email already exists', 'error')
        except Exception as e:
            flash('An error occurred during registration', 'error')
            print(f"Registration error: {e}")
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    # Update last login time before logging out
    if 'user_id' in session:
        users_collection.update_one(
            {'_id': ObjectId(session['user_id'])},
            {'$set': {'last_login': datetime.utcnow()}}
        )
    
    session.clear()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('index'))

@app.route('/forgot-password')
def forgot_password():
    return "Forgot password page - Coming soon!"

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash('Please login to view your profile', 'error')
        return redirect(url_for('login'))
    
    user = users_collection.find_one({'_id': ObjectId(session['user_id'])})
    if not user:
        session.clear()
        flash('User not found', 'error')
        return redirect(url_for('login'))
    
    return render_template('profile.html', user=user)

@app.route('/save-game-progress', methods=['POST'])
def save_game_progress():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    data = request.get_json()
    game_name = data.get('game_name')
    progress_data = data.get('progress_data')
    
    if not game_name:
        return jsonify({'success': False, 'message': 'Game name is required'}), 400
    
    try:
        # Remove any existing save for this game
        users_collection.update_one(
            {'_id': ObjectId(session['user_id'])},
            {'$pull': {'game_progress': {'game_name': game_name}}}
        )
        
        # Create new save
        save_data = {
            'game_name': game_name,
            'progress_data': progress_data,
            'last_saved': datetime.utcnow(),
            'type': 'cloud_save'
        }
        
        # Insert the new save
        users_collection.update_one(
            {'_id': ObjectId(session['user_id'])},
            {'$push': {'game_progress': save_data}}
        )
        
        return jsonify({
            'success': True, 
            'message': 'Game progress saved successfully',
            'timestamp': save_data['last_saved'].isoformat()
        })
        
    except Exception as e:
        print(f"Error saving game progress: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/delete-save-game', methods=['POST'])
def delete_save_game():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    data = request.get_json()
    game_name = data.get('game_name')
    
    if not game_name:
        return jsonify({'success': False, 'message': 'Game name is required'}), 400
    
    try:
        # Remove the game progress
        result = users_collection.update_one(
            {'_id': ObjectId(session['user_id'])},
            {'$pull': {'game_progress': {'game_name': game_name}}}
        )
        
        return jsonify({
            'success': True, 
            'message': 'Cloud save deleted successfully'
        })
        
    except Exception as e:
        print(f"Error deleting save game: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/get-game-progress/<game_name>')
def get_game_progress(game_name):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    try:
        user = users_collection.find_one({'_id': ObjectId(session['user_id'])})
        if user:
            # Find the most recent save for this game
            saves = [save for save in user.get('game_progress', []) 
                    if save['game_name'] == game_name]
            
            if saves:
                # Return the most recent save
                most_recent = max(saves, key=lambda x: x['last_saved'])
                return jsonify({
                    'success': True, 
                    'progress': most_recent,
                    'exists': True
                })
        
        return jsonify({
            'success': True, 
            'progress': None,
            'exists': False
        })
        
    except Exception as e:
        print(f"Error getting game progress: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500
    
if __name__ == '__main__':
    app.run(debug=True)