from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from src.models.ai_provider import db, AIProvider, AIPersonality
from src.services.ai_adapter import AIAdapterFactory
import json

ai_providers_bp = Blueprint('ai_providers', __name__)

@ai_providers_bp.route('/providers', methods=['GET'])
@cross_origin()
def get_providers():
    """Get all AI providers"""
    try:
        providers = AIProvider.query.filter_by(is_active=True).all()
        return jsonify({
            'success': True,
            'providers': [provider.to_dict() for provider in providers]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@ai_providers_bp.route('/providers', methods=['POST'])
@cross_origin()
def create_provider():
    """Create a new AI provider"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'api_type', 'api_key', 'default_model']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        # Validate API type
        if data['api_type'] not in AIAdapterFactory.get_supported_types():
            return jsonify({
                'success': False, 
                'error': f'Unsupported API type. Supported types: {AIAdapterFactory.get_supported_types()}'
            }), 400
        
        # Check if provider name already exists
        existing_provider = AIProvider.query.filter_by(name=data['name']).first()
        if existing_provider:
            return jsonify({'success': False, 'error': 'Provider name already exists'}), 400
        
        # Create new provider
        provider = AIProvider(
            name=data['name'],
            api_type=data['api_type'],
            api_base_url=data.get('api_base_url'),
            api_key=data['api_key'],
            default_model=data['default_model'],
            max_tokens=data.get('max_tokens', 1000),
            temperature=data.get('temperature', 0.7)
        )
        
        db.session.add(provider)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'provider': provider.to_dict(),
            'message': 'Provider created successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@ai_providers_bp.route('/providers/<int:provider_id>', methods=['PUT'])
@cross_origin()
def update_provider(provider_id):
    """Update an AI provider"""
    try:
        provider = AIProvider.query.get_or_404(provider_id)
        data = request.get_json()
        
        # Update fields
        if 'name' in data:
            # Check if new name already exists (excluding current provider)
            existing = AIProvider.query.filter(
                AIProvider.name == data['name'],
                AIProvider.id != provider_id
            ).first()
            if existing:
                return jsonify({'success': False, 'error': 'Provider name already exists'}), 400
            provider.name = data['name']
        
        if 'api_type' in data:
            if data['api_type'] not in AIAdapterFactory.get_supported_types():
                return jsonify({
                    'success': False, 
                    'error': f'Unsupported API type. Supported types: {AIAdapterFactory.get_supported_types()}'
                }), 400
            provider.api_type = data['api_type']
        
        if 'api_base_url' in data:
            provider.api_base_url = data['api_base_url']
        if 'api_key' in data:
            provider.api_key = data['api_key']
        if 'default_model' in data:
            provider.default_model = data['default_model']
        if 'max_tokens' in data:
            provider.max_tokens = data['max_tokens']
        if 'temperature' in data:
            provider.temperature = data['temperature']
        if 'is_active' in data:
            provider.is_active = data['is_active']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'provider': provider.to_dict(),
            'message': 'Provider updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@ai_providers_bp.route('/providers/<int:provider_id>', methods=['DELETE'])
@cross_origin()
def delete_provider(provider_id):
    """Delete an AI provider"""
    try:
        provider = AIProvider.query.get_or_404(provider_id)
        
        # Check if provider has personalities
        if provider.personalities:
            return jsonify({
                'success': False, 
                'error': 'Cannot delete provider with existing personalities. Delete personalities first.'
            }), 400
        
        db.session.delete(provider)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Provider deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@ai_providers_bp.route('/providers/<int:provider_id>/test', methods=['POST'])
@cross_origin()
def test_provider(provider_id):
    """Test an AI provider connection"""
    try:
        provider = AIProvider.query.get_or_404(provider_id)
        
        # Create adapter
        adapter = AIAdapterFactory.create_adapter(
            api_type=provider.api_type,
            api_key=provider.api_key,
            api_base_url=provider.api_base_url,
            model=provider.default_model,
            max_tokens=100,
            temperature=0.7
        )
        
        # Test message
        test_messages = adapter.format_messages(
            system_prompt="You are a helpful assistant. Respond with exactly: 'Connection test successful!'",
            user_message="Test connection"
        )
        
        result = adapter.send_message(test_messages)
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': 'Provider connection test successful',
                'response': result['content'],
                'usage': result.get('usage', {})
            })
        else:
            return jsonify({
                'success': False,
                'error': f"Provider test failed: {result['error']}"
            }), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@ai_providers_bp.route('/supported-types', methods=['GET'])
@cross_origin()
def get_supported_types():
    """Get supported AI provider types"""
    return jsonify({
        'success': True,
        'supported_types': AIAdapterFactory.get_supported_types()
    })

