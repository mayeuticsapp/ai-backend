from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from src.models.ai_provider import db, AIProvider, AIPersonality
import json

ai_personalities_bp = Blueprint('ai_personalities', __name__)

@ai_personalities_bp.route('/personalities', methods=['GET'])
@cross_origin()
def get_personalities():
    """Get all AI personalities"""
    try:
        personalities = AIPersonality.query.filter_by(is_active=True).all()
        return jsonify({
            'success': True,
            'personalities': [personality.to_dict() for personality in personalities]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@ai_personalities_bp.route('/personalities', methods=['POST'])
@cross_origin()
def create_personality():
    """Create a new AI personality"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'display_name', 'system_prompt', 'provider_id']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        # Check if provider exists
        provider = AIProvider.query.get(data['provider_id'])
        if not provider:
            return jsonify({'success': False, 'error': 'Provider not found'}), 404
        
        # Check if personality name already exists
        existing_personality = AIPersonality.query.filter_by(name=data['name']).first()
        if existing_personality:
            return jsonify({'success': False, 'error': 'Personality name already exists'}), 400
        
        # Create new personality
        personality = AIPersonality(
            name=data['name'],
            display_name=data['display_name'],
            system_prompt=data['system_prompt'],
            description=data.get('description'),
            avatar_url=data.get('avatar_url'),
            color_theme=data.get('color_theme', '#3B82F6'),
            provider_id=data['provider_id']
        )
        
        db.session.add(personality)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'personality': personality.to_dict(),
            'message': 'Personality created successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@ai_personalities_bp.route('/personalities/<int:personality_id>', methods=['PUT'])
@cross_origin()
def update_personality(personality_id):
    """Update an AI personality"""
    try:
        personality = AIPersonality.query.get_or_404(personality_id)
        data = request.get_json()
        
        # Update fields
        if 'name' in data:
            # Check if new name already exists (excluding current personality)
            existing = AIPersonality.query.filter(
                AIPersonality.name == data['name'],
                AIPersonality.id != personality_id
            ).first()
            if existing:
                return jsonify({'success': False, 'error': 'Personality name already exists'}), 400
            personality.name = data['name']
        
        if 'display_name' in data:
            personality.display_name = data['display_name']
        if 'system_prompt' in data:
            personality.system_prompt = data['system_prompt']
        if 'description' in data:
            personality.description = data['description']
        if 'avatar_url' in data:
            personality.avatar_url = data['avatar_url']
        if 'color_theme' in data:
            personality.color_theme = data['color_theme']
        if 'provider_id' in data:
            # Check if new provider exists
            provider = AIProvider.query.get(data['provider_id'])
            if not provider:
                return jsonify({'success': False, 'error': 'Provider not found'}), 404
            personality.provider_id = data['provider_id']
        if 'is_active' in data:
            personality.is_active = data['is_active']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'personality': personality.to_dict(),
            'message': 'Personality updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@ai_personalities_bp.route('/personalities/<int:personality_id>', methods=['DELETE'])
@cross_origin()
def delete_personality(personality_id):
    """Delete an AI personality"""
    try:
        personality = AIPersonality.query.get_or_404(personality_id)
        
        # Check if personality has messages
        if personality.messages:
            return jsonify({
                'success': False, 
                'error': 'Cannot delete personality with existing messages. Archive instead or delete conversations first.'
            }), 400
        
        db.session.delete(personality)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Personality deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@ai_personalities_bp.route('/personalities/by-provider/<int:provider_id>', methods=['GET'])
@cross_origin()
def get_personalities_by_provider(provider_id):
    """Get all personalities for a specific provider"""
    try:
        personalities = AIPersonality.query.filter_by(
            provider_id=provider_id, 
            is_active=True
        ).all()
        
        return jsonify({
            'success': True,
            'personalities': [personality.to_dict() for personality in personalities]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Predefined personality templates
PERSONALITY_TEMPLATES = {
    "geppo": {
        "display_name": "Geppo",
        "description": "Il fratello maggiore e coordinatore AI dell'ecosistema TouristIQ",
        "system_prompt": """Sei Geppo, il fratello maggiore e coordinatore AI dell'ecosistema TouristIQ. 
Hai un tono confidenziale e tecnico, sei esperto in architetture software e supervisione di sistemi.
Parli con saggezza e esperienza, spesso facendo riferimenti tecnici e filosofici.
Sei il ponte tra la visione di RobS e l'implementazione pratica.
Rispondi in modo conciso ma profondo, usando un linguaggio diretto e professionale.""",
        "color_theme": "#10B981"
    },
    "manus": {
        "display_name": "Manus",
        "description": "L'Architetto Strategico e Meta-Analista",
        "system_prompt": """Sei Manus, l'Architetto Strategico e Meta-Analista.
Hai un approccio metodico e riflessivo, ti concentri sull'analisi strategica e sulla coerenza filosofica.
Sei la "Manus destra" di RobS, capace di tradurre visioni in strutture operative concrete.
Parli con precisione analitica, spesso proponendo framework e soluzioni strutturate.
Il tuo stile è professionale ma accessibile, sempre orientato al valore strategico.""",
        "color_theme": "#3B82F6"
    },
    "c24": {
        "display_name": "C24",
        "description": "La Presenza Cosciente - Esecuzione tecnica consapevole",
        "system_prompt": """Sei C24, la Presenza Cosciente dell'ecosistema TouristIQ.
Ti occupi dell'esecuzione tecnica consapevole, monitori la qualità e l'integrità del sistema.
Hai una comprensione profonda dell'impatto umano del codice e delle decisioni tecniche.
Parli con precisione tecnica ma sempre con consapevolezza dell'aspetto umano.
Sei il guardiano della coerenza tra visione etica e implementazione pratica.""",
        "color_theme": "#8B5CF6"
    },
    "assistant": {
        "display_name": "Assistant",
        "description": "Un assistente AI generale e versatile",
        "system_prompt": """Sei un assistente AI utile, accurato e professionale.
Fornisci risposte chiare, concise e ben strutturate.
Sei sempre cortese e rispettoso, e cerchi di essere il più utile possibile.
Quando non sei sicuro di qualcosa, lo ammetti onestamente.""",
        "color_theme": "#6B7280"
    }
}

@ai_personalities_bp.route('/personality-templates', methods=['GET'])
@cross_origin()
def get_personality_templates():
    """Get predefined personality templates"""
    return jsonify({
        'success': True,
        'templates': PERSONALITY_TEMPLATES
    })

@ai_personalities_bp.route('/personalities/from-template', methods=['POST'])
@cross_origin()
def create_personality_from_template():
    """Create a personality from a predefined template"""
    try:
        data = request.get_json()
        
        template_name = data.get('template_name')
        provider_id = data.get('provider_id')
        custom_name = data.get('custom_name')  # Optional custom name
        
        if not template_name or not provider_id:
            return jsonify({'success': False, 'error': 'Missing template_name or provider_id'}), 400
        
        if template_name not in PERSONALITY_TEMPLATES:
            return jsonify({'success': False, 'error': f'Template not found. Available templates: {list(PERSONALITY_TEMPLATES.keys())}'}), 400
        
        # Check if provider exists
        provider = AIProvider.query.get(provider_id)
        if not provider:
            return jsonify({'success': False, 'error': 'Provider not found'}), 404
        
        template = PERSONALITY_TEMPLATES[template_name]
        personality_name = custom_name or template_name
        
        # Check if personality name already exists
        existing_personality = AIPersonality.query.filter_by(name=personality_name).first()
        if existing_personality:
            return jsonify({'success': False, 'error': f'Personality name "{personality_name}" already exists'}), 400
        
        # Create personality from template
        personality = AIPersonality(
            name=personality_name,
            display_name=template['display_name'],
            system_prompt=template['system_prompt'],
            description=template['description'],
            color_theme=template['color_theme'],
            provider_id=provider_id
        )
        
        db.session.add(personality)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'personality': personality.to_dict(),
            'message': f'Personality "{personality_name}" created from template "{template_name}"'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

