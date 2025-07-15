import os
import sys
# DON\'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from src.models.ai_provider import db, AIProvider, AIPersonality, Conversation, ChatMessage
from src.routes.user import user_bp
from src.routes.ai_providers import ai_providers_bp
from src.routes.ai_personalities import ai_personalities_bp
from src.routes.conversations import conversations_bp

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'

# Enable CORS for specific origins
# Ho modificato questa riga per essere più esplicito sulle origini permesse
CORS(app, resources={r"/api/*": {"origins": [
    "https://ai-frontend-iyvt.onrender.com", # Il tuo frontend su Render
    "http://localhost:5173", # Per lo sviluppo locale del frontend (se usi la porta predefinita di Vite )
    # Aggiungi qui altre origini se necessario per lo sviluppo locale o altri ambienti
]}})

# Register blueprints
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(ai_providers_bp, url_prefix='/api')
app.register_blueprint(ai_personalities_bp, url_prefix='/api')
app.register_blueprint(conversations_bp, url_prefix='/api')

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

with app.app_context():
    db.create_all()
    
    # Create default OpenAI provider if it doesn't exist
    existing_provider = AIProvider.query.filter_by(name='OpenAI Default').first()
    if not existing_provider:
        default_provider = AIProvider(
            name='OpenAI Default',
            api_type='openai',
            api_base_url=os.getenv('OPENAI_API_BASE', 'https://api.openai.com/v1' ),
            api_key=os.getenv('OPENAI_API_KEY', ''),
            default_model='gpt-4',
            max_tokens=1000,
            temperature=0.7
        )
        db.session.add(default_provider)
        db.session.commit()
        print("Created default OpenAI provider")

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    # Escludi le route API dalla gestione dei file statici
    if path.startswith('api/'):
        return "API endpoint not found", 404
    
    static_folder_path = app.static_folder
    if static_folder_path is None:
        return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
