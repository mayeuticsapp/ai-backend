import openai
import requests
import json
from typing import Dict, List, Any, Optional

class AIAdapter:
    """Base class for AI adapters"""
    
    def __init__(self, api_key: str, api_base_url: str, model: str, max_tokens: int = 1000, temperature: float = 0.7):
        self.api_key = api_key
        self.api_base_url = api_base_url
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
    
    def format_messages(self, system_prompt: str, user_message: str, conversation_history: List[Dict] = None) -> List[Dict]:
        """Format messages for the AI API"""
        messages = []
        
        # Add system prompt
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        # Add conversation history
        if conversation_history:
            for msg in conversation_history[-5:]:  # Last 5 messages for context
                if msg.get('sender_type') == 'ai' and msg.get('content'):
                    messages.append({
                        "role": "assistant",
                        "content": msg['content']
                    })
                elif msg.get('sender_type') == 'user' and msg.get('content'):
                    messages.append({
                        "role": "user",
                        "content": msg['content']
                    })
        
        # Add current user message
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        return messages
    
    def send_message(self, messages: List[Dict]) -> Dict[str, Any]:
        """Send message to AI and get response"""
        raise NotImplementedError("Subclasses must implement send_message")

class OpenAIAdapter(AIAdapter):
    """OpenAI API adapter"""
    
    def __init__(self, api_key: str, api_base_url: str = "https://api.openai.com/v1", model: str = "gpt-4", max_tokens: int = 1000, temperature: float = 0.7):
        super().__init__(api_key, api_base_url, model, max_tokens, temperature)
        
        # Configure OpenAI client
        openai.api_key = self.api_key
        if api_base_url != "https://api.openai.com/v1":
            openai.api_base = api_base_url
    
    def send_message(self, messages: List[Dict]) -> Dict[str, Any]:
        """Send message to OpenAI API"""
        try:
            # Validate API key
            if not self.api_key or self.api_key.strip() == "":
                return {
                    'success': False,
                    'error': 'API key is missing or empty',
                    'content': None
                }
            
            # Make API call
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                timeout=30
            )
            
            # Extract response
            content = response.choices[0].message.content
            usage = response.usage._asdict() if hasattr(response.usage, '_asdict') else dict(response.usage)
            
            return {
                'success': True,
                'content': content,
                'usage': usage,
                'model': response.model,
                'provider': 'openai'
            }
            
        except openai.error.AuthenticationError as e:
            return {
                'success': False,
                'error': f'Authentication failed: {str(e)}',
                'content': None
            }
        except openai.error.RateLimitError as e:
            return {
                'success': False,
                'error': f'Rate limit exceeded: {str(e)}',
                'content': None
            }
        except openai.error.APIError as e:
            return {
                'success': False,
                'error': f'OpenAI API error: {str(e)}',
                'content': None
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}',
                'content': None
            }

class ManusAdapter(AIAdapter):
    """Manus API adapter"""
    
    def send_message(self, messages: List[Dict]) -> Dict[str, Any]:
        """Send message to Manus API"""
        try:
            # Validate API key
            if not self.api_key or self.api_key.strip() == "":
                return {
                    'success': False,
                    'error': 'API key is missing or empty',
                    'content': None
                }
            
            # Prepare request
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': self.model,
                'messages': messages,
                'max_tokens': self.max_tokens,
                'temperature': self.temperature
            }
            
            # Make API call
            response = requests.post(
                f"{self.api_base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                return {
                    'success': True,
                    'content': content,
                    'usage': result.get('usage', {}),
                    'model': result.get('model', self.model),
                    'provider': 'manus'
                }
            else:
                return {
                    'success': False,
                    'error': f'API request failed with status {response.status_code}: {response.text}',
                    'content': None
                }
                
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': 'Request timeout',
                'content': None
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Request error: {str(e)}',
                'content': None
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}',
                'content': None
            }

class AIAdapterFactory:
    """Factory for creating AI adapters"""
    
    @staticmethod
    def create_adapter(api_type: str, api_key: str, api_base_url: str, model: str, max_tokens: int = 1000, temperature: float = 0.7) -> AIAdapter:
        """Create appropriate AI adapter based on API type"""
        
        if api_type.lower() == 'openai':
            return OpenAIAdapter(
                api_key=api_key,
                api_base_url=api_base_url,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature
            )
        elif api_type.lower() == 'manus':
            return ManusAdapter(
                api_key=api_key,
                api_base_url=api_base_url,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature
            )
        else:
            raise ValueError(f"Unsupported API type: {api_type}")
    
    @staticmethod
    def get_supported_types() -> List[str]:
        """Get list of supported API types"""
        return ['openai', 'manus']

