from datetime import datetime
import json

from . import db  # ✅ importa l'istanza db dallo stesso package

class AIProvider(db.Model):
    __tablename__ = 'ai_providers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    api_type = db.Column(db.String(50), nullable=False)
    api_base_url = db.Column(db.String(255), nullable=True)
    api_key = db.Column(db.Text, nullable=False)
    default_model = db.Column(db.String(100), nullable=False)
    max_tokens = db.Column(db.Integer, default=1000)
    temperature = db.Column(db.Float, default=0.7)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    personalities = db.relationship('AIPersonality', backref='provider', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'api_type': self.api_type,
            'api_base_url': self.api_base_url,
            'default_model': self.default_model,
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'personalities_count': len(self.personalities)
        }

class AIPersonality(db.Model):
    __tablename__ = 'ai_personalities'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    display_name = db.Column(db.String(100), nullable=False)
    system_prompt = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, nullable=True)
    avatar_url = db.Column(db.String(255), nullable=True)
    color_theme = db.Column(db.String(7), default='#3B82F6')
    provider_id = db.Column(db.Integer, db.ForeignKey('ai_providers.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    messages = db.relationship('ChatMessage', backref='personality', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'system_prompt': self.system_prompt,
            'description': self.description,
            'avatar_url': self.avatar_url,
            'color_theme': self.color_theme,
            'provider_id': self.provider_id,
            'provider_name': self.provider.name if self.provider else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Conversation(db.Model):
    __tablename__ = 'conversations'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    topic = db.Column(db.Text, nullable=True)
    participants = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    messages = db.relationship('ChatMessage', backref='conversation', lazy=True, cascade='all, delete-orphan')
    
    def get_participants(self):
        try:
            return json.loads(self.participants) if self.participants else []
        except:
            return []
    
    def set_participants(self, participant_ids):
        self.participants = json.dumps(participant_ids)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'topic': self.topic,
            'participants': self.get_participants(),
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'message_count': len(self.messages)
        }

class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=False)
    personality_id = db.Column(db.Integer, db.ForeignKey('ai_personalities.id'), nullable=True)
    content = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(20), default='text')
    sender_type = db.Column(db.String(20), default='ai')
    message_metadata = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_metadata(self):
        try:
            return json.loads(self.message_metadata) if self.message_metadata else {}
        except:
            return {}
    
    def set_metadata(self, data):
        self.message_metadata = json.dumps(data) if data else None
    
    def to_dict(self):
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'personality_id': self.personality_id,
            'personality_name': self.personality.name if self.personality else None,
            'personality_display_name': self.personality.display_name if self.personality else None,
            'personality_color': self.personality.color_theme if self.personality else '#6B7280',
            'content': self.content,
            'message_type': self.message_type,
            'sender_type': self.sender_type,
            'metadata': self.get_metadata(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
