from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from src.models.ai_provider import db, AIProvider, AIPersonality, Conversation, ChatMessage
from src.services.ai_adapter import AIAdapterFactory
import json
from datetime import datetime

conversations_bp = Blueprint('conversations', __name__)

@conversations_bp.route('/conversations', methods=['GET'])
@cross_origin()
def get_conversations():
    """Get all conversations"""
    try:
        conversations = Conversation.query.order_by(Conversation.updated_at.desc()).all()
        return jsonify({
            'success': True,
            'conversations': [conv.to_dict() for conv in conversations]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@conversations_bp.route('/conversations', methods=['POST'])
@cross_origin()
def create_conversation():
    """Create a new conversation"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['title', 'participants']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        participants = data['participants']
        if not isinstance(participants, list) or len(participants) < 2:
            return jsonify({'success': False, 'error': 'At least 2 participants required'}), 400
        
        # Validate that all participants exist and are active
        for participant_id in participants:
            personality = AIPersonality.query.get(participant_id)
            if not personality or not personality.is_active:
                return jsonify({'success': False, 'error': f'Personality {participant_id} not found or inactive'}), 400
        
        # Create new conversation
        conversation = Conversation(
            title=data['title'],
            topic=data.get('topic'),
            participants=json.dumps(participants)
        )
        
        db.session.add(conversation)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'conversation': conversation.to_dict(),
            'message': 'Conversation created successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@conversations_bp.route('/conversations/<int:conversation_id>', methods=['GET'])
@cross_origin()
def get_conversation(conversation_id):
    """Get a specific conversation with messages"""
    try:
        conversation = Conversation.query.get_or_404(conversation_id)
        messages = ChatMessage.query.filter_by(conversation_id=conversation_id).order_by(ChatMessage.created_at.asc()).all()
        
        # Get participant details
        participant_ids = conversation.get_participants()
        participants = []
        for pid in participant_ids:
            personality = AIPersonality.query.get(pid)
            if personality:
                participants.append(personality.to_dict())
        
        return jsonify({
            'success': True,
            'conversation': conversation.to_dict(),
            'participants': participants,
            'messages': [msg.to_dict() for msg in messages]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@conversations_bp.route('/conversations/<int:conversation_id>/messages', methods=['POST'])
@cross_origin()
def send_message(conversation_id):
    """Send a message in a conversation"""
    try:
        conversation = Conversation.query.get_or_404(conversation_id)
        data = request.get_json()
        
        personality_id = data.get('personality_id')
        content = data.get('content')
        sender_type = data.get('sender_type', 'ai')  # 'ai' or 'user'
        
        if not content:
            return jsonify({'success': False, 'error': 'Message content is required'}), 400
        
        if sender_type == 'ai' and not personality_id:
            return jsonify({'success': False, 'error': 'Personality ID required for AI messages'}), 400
        
        # If it's an AI message, validate personality and get response
        if sender_type == 'ai':
            personality = AIPersonality.query.get(personality_id)
            if not personality or not personality.is_active:
                return jsonify({'success': False, 'error': 'Personality not found or inactive'}), 400
            
            # Check if personality is part of this conversation
            if personality_id not in conversation.get_participants():
                return jsonify({'success': False, 'error': 'Personality not part of this conversation'}), 400
            
            # Get conversation history for context
            recent_messages = ChatMessage.query.filter_by(
                conversation_id=conversation_id
            ).order_by(ChatMessage.created_at.desc()).limit(10).all()
            
            # Create AI adapter
            provider = personality.provider
            adapter = AIAdapterFactory.create_adapter(
                api_type=provider.api_type,
                api_key=provider.api_key,
                api_base_url=provider.api_base_url,
                model=provider.default_model,
                max_tokens=provider.max_tokens,
                temperature=provider.temperature
            )
            
            # Format messages for AI
            messages = adapter.format_messages(
                system_prompt=personality.system_prompt,
                user_message=content,
                conversation_history=[msg.to_dict() for msg in reversed(recent_messages)]
            )
            
            # Get AI response
            result = adapter.send_message(messages)
            
            if not result['success']:
                return jsonify({'success': False, 'error': f'AI response failed: {result["error"]}'}), 500
            
            # Create message with AI response
            message = ChatMessage(
                conversation_id=conversation_id,
                personality_id=personality_id,
                content=result['content'],
                sender_type='ai',
                metadata=json.dumps({
                    'usage': result.get('usage', {}),
                    'model': result.get('model'),
                    'provider': result.get('provider')
                })
            )
        else:
            # User message
            message = ChatMessage(
                conversation_id=conversation_id,
                personality_id=None,
                content=content,
                sender_type='user'
            )
        
        db.session.add(message)
        
        # Update conversation timestamp
        conversation.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': message.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@conversations_bp.route('/conversations/<int:conversation_id>/auto-continue', methods=['POST'])
@cross_origin()
def auto_continue_conversation(conversation_id):
    """Automatically continue conversation between AIs"""
    try:
        conversation = Conversation.query.get_or_404(conversation_id)
        data = request.get_json()
        
        rounds = data.get('rounds', 1)  # Number of back-and-forth rounds
        if rounds < 1 or rounds > 10:
            return jsonify({'success': False, 'error': 'Rounds must be between 1 and 10'}), 400
        
        participants = conversation.get_participants()
        if len(participants) < 2:
            return jsonify({'success': False, 'error': 'Need at least 2 participants for auto-continue'}), 400
        
        # Get the last message to determine who should respond next
        last_message = ChatMessage.query.filter_by(
            conversation_id=conversation_id
        ).order_by(ChatMessage.created_at.desc()).first()
        
        if not last_message:
            return jsonify({'success': False, 'error': 'No messages in conversation to continue from'}), 400
        
        new_messages = []
        current_speaker_idx = 0
        
        # Determine next speaker
        if last_message.personality_id:
            try:
                current_speaker_idx = participants.index(last_message.personality_id)
                current_speaker_idx = (current_speaker_idx + 1) % len(participants)
            except ValueError:
                current_speaker_idx = 0
        
        # Generate conversation rounds
        for round_num in range(rounds):
            for turn in range(len(participants)):
                speaker_id = participants[(current_speaker_idx + turn) % len(participants)]
                personality = AIPersonality.query.get(speaker_id)
                
                if not personality or not personality.is_active:
                    continue
                
                # Get recent conversation history
                recent_messages = ChatMessage.query.filter_by(
                    conversation_id=conversation_id
                ).order_by(ChatMessage.created_at.desc()).limit(10).all()
                
                # Create context message for the AI
                if recent_messages:
                    last_msg = recent_messages[0]
                    if last_msg.personality_id and last_msg.personality_id != speaker_id:
                        other_personality = AIPersonality.query.get(last_msg.personality_id)
                        context_message = f"{other_personality.display_name if other_personality else 'Someone'} ha detto: \"{last_msg.content}\". Rispondi a questa affermazione continuando la conversazione."
                    else:
                        context_message = "Continua la conversazione basandoti sui messaggi precedenti."
                else:
                    context_message = "Inizia o continua la conversazione."
                
                # Create AI adapter
                provider = personality.provider
                adapter = AIAdapterFactory.create_adapter(
                    api_type=provider.api_type,
                    api_key=provider.api_key,
                    api_base_url=provider.api_base_url,
                    model=provider.default_model,
                    max_tokens=provider.max_tokens,
                    temperature=provider.temperature
                )
                
                # Format messages for AI
                messages = adapter.format_messages(
                    system_prompt=personality.system_prompt,
                    user_message=context_message,
                    conversation_history=[msg.to_dict() for msg in reversed(recent_messages)]
                )
                
                # Get AI response
                result = adapter.send_message(messages)
                
                if result['success']:
                    # Create message
                    message = ChatMessage(
                        conversation_id=conversation_id,
                        personality_id=speaker_id,
                        content=result['content'],
                        sender_type='ai',
                        metadata=json.dumps({
                            'usage': result.get('usage', {}),
                            'model': result.get('model'),
                            'provider': result.get('provider'),
                            'auto_generated': True,
                            'round': round_num + 1,
                            'turn': turn + 1
                        })
                    )
                    
                    db.session.add(message)
                    new_messages.append(message)
        
        # Update conversation timestamp
        conversation.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'new_messages': [msg.to_dict() for msg in new_messages],
            'message': f'Generated {len(new_messages)} new messages'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@conversations_bp.route('/conversations/<int:conversation_id>', methods=['PUT'])
@cross_origin()
def update_conversation(conversation_id):
    """Update conversation details"""
    try:
        conversation = Conversation.query.get_or_404(conversation_id)
        data = request.get_json()
        
        if 'title' in data:
            conversation.title = data['title']
        if 'topic' in data:
            conversation.topic = data['topic']
        if 'status' in data:
            conversation.status = data['status']
        if 'participants' in data:
            participants = data['participants']
            if not isinstance(participants, list) or len(participants) < 2:
                return jsonify({'success': False, 'error': 'At least 2 participants required'}), 400
            
            # Validate participants
            for participant_id in participants:
                personality = AIPersonality.query.get(participant_id)
                if not personality:
                    return jsonify({'success': False, 'error': f'Personality {participant_id} not found'}), 400
            
            conversation.set_participants(participants)
        
        conversation.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'conversation': conversation.to_dict(),
            'message': 'Conversation updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@conversations_bp.route('/conversations/<int:conversation_id>', methods=['DELETE'])
@cross_origin()
def delete_conversation(conversation_id):
    """Delete a conversation and all its messages"""
    try:
        conversation = Conversation.query.get_or_404(conversation_id)
        
        db.session.delete(conversation)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Conversation deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

