"""
AI Adapter Service - Handles different AI API providers
Supports OpenAI, Anthropic, Google, and other providers through a unified interface
"""

import openai
import requests
import json
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import os

class AIAdapter(ABC):
    """Abstract base class for AI adapters"""
    
    def __init__(self, api_key: str, api_base_url: Optional[str] = None, model: str = "gpt-4", **kwargs):
        self.api_key = api_key
        self.api_base_url = api_base_url
        self.model = model
        self.max_tokens = kwargs.get('max_tokens', 1000)
        self.temperature = kwargs.get('temperature', 0.7)
    
    @abstractmethod
    def send_message(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Send message to AI and return response"""
        pass
    
    @abstractmethod
    def format_messages(self, system_prompt: str, user_message: str, conversation_history: List[Dict] = None) -> List[Dict[str, str]]:
        """Format messages for the specific API"""
        pass

class OpenAIAdapter(AIAdapter):
    """Adapter for OpenAI API (GPT models)"""
    
    def __init__(self, api_key: str, api_base_url: Optional[str] = None, model: str = "gpt-4", **kwargs):
        super().__init__(api_key, api_base_url, model, **kwargs)
        
        # Configure OpenAI client
        openai.api_key = self.api_key
        if self.api_base_url:
            openai.api_base = self.api_base_url
    
    def send_message(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Send message to OpenAI API"""
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=messages,
                max_tokens=kwargs.get('max_tokens', self.max_tokens),
                temperature=kwargs.get('temperature', self.temperature),
                **kwargs
            )
            
            return {
                'success': True,
                'content': response.choices[0].message.content,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                },
                'model': response.model,
                'provider': 'openai'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'provider': 'openai'
            }
    
    def format_messages(self, system_prompt: str, user_message: str, conversation_history: List[Dict] = None) -> List[Dict[str, str]]:
        """Format messages for OpenAI API"""
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history
        if conversation_history:
            for msg in conversation_history[-10:]:  # Last 10 messages for context
                if msg.get('sender_type') == 'user':
                    messages.append({"role": "user", "content": msg['content']})
                elif msg.get('sender_type') == 'ai':
                    messages.append({"role": "assistant", "content": msg['content']})
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        return messages

class AnthropicAdapter(AIAdapter):
    """Adapter for Anthropic API (Claude models)"""
    
    def __init__(self, api_key: str, api_base_url: Optional[str] = None, model: str = "claude-3-sonnet-20240229", **kwargs):
        super().__init__(api_key, api_base_url or "https://api.anthropic.com", model, **kwargs)
    
    def send_message(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Send message to Anthropic API"""
        try:
            # Extract system message
            system_message = ""
            user_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    user_messages.append(msg)
            
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01"
            }
            
            payload = {
                "model": self.model,
                "max_tokens": kwargs.get('max_tokens', self.max_tokens),
                "temperature": kwargs.get('temperature', self.temperature),
                "system": system_message,
                "messages": user_messages
            }
            
            response = requests.post(
                f"{self.api_base_url}/v1/messages",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'content': data['content'][0]['text'],
                    'usage': {
                        'prompt_tokens': data.get('usage', {}).get('input_tokens', 0),
                        'completion_tokens': data.get('usage', {}).get('output_tokens', 0),
                        'total_tokens': data.get('usage', {}).get('input_tokens', 0) + data.get('usage', {}).get('output_tokens', 0)
                    },
                    'model': data.get('model', self.model),
                    'provider': 'anthropic'
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}",
                    'provider': 'anthropic'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'provider': 'anthropic'
            }
    
    def format_messages(self, system_prompt: str, user_message: str, conversation_history: List[Dict] = None) -> List[Dict[str, str]]:
        """Format messages for Anthropic API"""
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history
        if conversation_history:
            for msg in conversation_history[-10:]:
                if msg.get('sender_type') == 'user':
                    messages.append({"role": "user", "content": msg['content']})
                elif msg.get('sender_type') == 'ai':
                    messages.append({"role": "assistant", "content": msg['content']})
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        return messages

class GoogleAdapter(AIAdapter):
    """Adapter for Google AI API (Gemini models)"""
    
    def __init__(self, api_key: str, api_base_url: Optional[str] = None, model: str = "gemini-pro", **kwargs):
        super().__init__(api_key, api_base_url or "https://generativelanguage.googleapis.com", model, **kwargs)
    
    def send_message(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Send message to Google AI API"""
        try:
            # Convert messages to Google format
            contents = []
            system_instruction = ""
            
            for msg in messages:
                if msg["role"] == "system":
                    system_instruction = msg["content"]
                elif msg["role"] == "user":
                    contents.append({"role": "user", "parts": [{"text": msg["content"]}]})
                elif msg["role"] == "assistant":
                    contents.append({"role": "model", "parts": [{"text": msg["content"]}]})
            
            headers = {
                "Content-Type": "application/json"
            }
            
            payload = {
                "contents": contents,
                "generationConfig": {
                    "maxOutputTokens": kwargs.get('max_tokens', self.max_tokens),
                    "temperature": kwargs.get('temperature', self.temperature)
                }
            }
            
            if system_instruction:
                payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
            
            url = f"{self.api_base_url}/v1beta/models/{self.model}:generateContent?key={self.api_key}"
            
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                content = data['candidates'][0]['content']['parts'][0]['text']
                
                return {
                    'success': True,
                    'content': content,
                    'usage': {
                        'prompt_tokens': data.get('usageMetadata', {}).get('promptTokenCount', 0),
                        'completion_tokens': data.get('usageMetadata', {}).get('candidatesTokenCount', 0),
                        'total_tokens': data.get('usageMetadata', {}).get('totalTokenCount', 0)
                    },
                    'model': self.model,
                    'provider': 'google'
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}",
                    'provider': 'google'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'provider': 'google'
            }
    
    def format_messages(self, system_prompt: str, user_message: str, conversation_history: List[Dict] = None) -> List[Dict[str, str]]:
        """Format messages for Google AI API"""
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history
        if conversation_history:
            for msg in conversation_history[-10:]:
                if msg.get('sender_type') == 'user':
                    messages.append({"role": "user", "content": msg['content']})
                elif msg.get('sender_type') == 'ai':
                    messages.append({"role": "assistant", "content": msg['content']})
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        return messages

class AIAdapterFactory:
    """Factory class to create appropriate AI adapters"""
    
    ADAPTERS = {
        'openai': OpenAIAdapter,
        'anthropic': AnthropicAdapter,
        'google': GoogleAdapter
    }
    
    @classmethod
    def create_adapter(cls, api_type: str, **kwargs) -> AIAdapter:
        """Create an AI adapter based on the API type"""
        if api_type not in cls.ADAPTERS:
            raise ValueError(f"Unsupported API type: {api_type}. Supported types: {list(cls.ADAPTERS.keys())}")
        
        adapter_class = cls.ADAPTERS[api_type]
        return adapter_class(**kwargs)
    
    @classmethod
    def get_supported_types(cls) -> List[str]:
        """Get list of supported API types"""
        return list(cls.ADAPTERS.keys())

