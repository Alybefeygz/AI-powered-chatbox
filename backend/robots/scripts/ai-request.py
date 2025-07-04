#!/usr/bin/env python3
"""
AI Request Script for SidrexGPT Robots App - OpenRouter Integration
"""

import requests
import json
import logging
import os
import time
import random
from typing import Dict, Any, Optional, List

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Available models with fallback
MODELS = [
    "qwen/qwen3-30b-a3b:free",                    # Ana model (dengeli)
    "openrouter/cypher-alpha:free",               # Yedek 1 (uzun context)
    "meta-llama/llama-4-scout:free",              # Yedek 2 (görsel anlama)
    "qwen/qwen3-14b:free",                        # Yedek 3 (çok dilli)
    "deepseek/deepseek-r1-distill-llama-70b:free",# Yedek 4 (güçlü)
    "qwen/qwen3-4b:free"                          # Yedek 5 (hızlı)
]

class OpenRouterAIHandler:
    """
    Handler class for OpenRouter AI API requests
    """
    
    def __init__(self, api_key: Optional[str] = None, app_name: str = "SidrexGPT"):
        """
        Initialize the OpenRouter AI Handler
        
        Args:
            api_key: OpenRouter API key (REQUIRED)
            app_name: Application name for the requests
        """
        if not api_key:
            raise ValueError("❌ OpenRouter API key is required! Please provide a valid API key.")
        
        self.api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1"
        self.app_name = app_name
        self.session = requests.Session()
        self.current_model_index = 0  # Track current model index
        self.model_error_counts = {model: 0 for model in MODELS}  # Track errors per model
        
        # Set headers for OpenRouter
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",  # SidrexGPT local development
            "X-Title": self.app_name
        })
    
    def get_next_model(self) -> str:
        """
        Get next available model from the rotation
        
        Returns:
            Next model ID to try
        """
        # Reset error counts periodically (every hour)
        current_time = time.time()
        if not hasattr(self, 'last_reset_time') or current_time - self.last_reset_time > 3600:
            self.model_error_counts = {model: 0 for model in MODELS}
            self.last_reset_time = current_time
        
        # Try to find a model with fewer errors
        min_errors = min(self.model_error_counts.values())
        available_models = [model for model in MODELS if self.model_error_counts[model] <= min_errors + 2]
        
        if not available_models:
            # If all models have too many errors, reset counts and try again
            self.model_error_counts = {model: 0 for model in MODELS}
            available_models = MODELS
        
        # Rotate through available models
        self.current_model_index = (self.current_model_index + 1) % len(available_models)
        return available_models[self.current_model_index]
    
    def make_chat_request(self, messages: list, model: str = None, max_retries: int = 3) -> Dict[str, Any]:
        """
        Make a chat completion request to OpenRouter with retry and model rotation
        
        Args:
            messages: List of chat messages
            model: Model to use (if None, will use model rotation)
            max_retries: Maximum number of retries per model
            
        Returns:
            Response data as dictionary
        """
        if model is None:
            model = MODELS[0]  # Start with first model
        
        original_model = model
        total_attempts = 0
        max_total_attempts = len(MODELS) * max_retries
        
        while total_attempts < max_total_attempts:
            url = f"{self.base_url}/chat/completions"
            
            data = {
                "model": model,
                "messages": messages,
                "max_tokens": 1000,
                "temperature": 0.7,
                "top_p": 1,
                "frequency_penalty": 0,
                "presence_penalty": 0
            }
            
            try:
                response = self.session.post(url, json=data)
                response.raise_for_status()
                
                # Success - reset error count for this model
                self.model_error_counts[model] = max(0, self.model_error_counts[model] - 1)
                logger.info(f"Successful chat request with model: {model}")
                return response.json()
                
            except requests.exceptions.HTTPError as e:
                self.model_error_counts[model] += 1
                
                if e.response.status_code == 429:  # Rate limit error
                    wait_time = (2 ** (total_attempts % 3)) + random.uniform(0, 1)
                    logger.warning(f"Rate limit hit for {model}. Waiting {wait_time:.2f}s before trying next model...")
                    time.sleep(wait_time)
                
                # Try next model
                model = self.get_next_model()
                if model == original_model:  # We've tried all models
                    total_attempts += max_retries
                else:
                    total_attempts += 1
                continue
                    
            except requests.exceptions.RequestException as e:
                self.model_error_counts[model] += 1
                logger.error(f"Chat request failed with {model}: {e}")
                
                # Try next model
                model = self.get_next_model()
                if model == original_model:  # We've tried all models
                    total_attempts += max_retries
                else:
                    total_attempts += 1
                continue
        
        # If we get here, all models failed
        logger.error("All models failed after maximum attempts")
        return {"error": "Tüm modeller şu anda meşgul. Lütfen birkaç dakika bekleyip tekrar deneyin."}
    
    def get_available_models(self) -> Dict[str, Any]:
        """
        Get list of available models from OpenRouter
        
        Returns:
            Dictionary containing available models
        """
        try:
            url = f"{self.base_url}/models"
            response = self.session.get(url)
            response.raise_for_status()
            
            logger.info("Successfully retrieved available models")
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get models: {e}")
            raise
    
    def ask_question(self, question: str, model: str = None, system_prompt: Optional[str] = None) -> str:
        """
        Ask a simple question to the AI
        
        Args:
            question: The question to ask
            model: Model to use (if None, will use model rotation)
            system_prompt: Optional system prompt to set AI behavior
            
        Returns:
            AI response as string
        """
        messages = []
        
        # Add system prompt if provided
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Add user question
        messages.append({"role": "user", "content": question})
        
        try:
            response = self.make_chat_request(messages, model)
            
            # Check if response contains an error
            if "error" in response:
                return response["error"]
            
            ai_response = response["choices"][0]["message"]["content"]
            
            logger.info(f"Question: {question[:50]}...")
            logger.info(f"Response: {ai_response[:100]}...")
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Error asking question: {e}")
            return f"Üzgünüm, şu anda teknik bir sorun yaşıyorum. Lütfen daha sonra tekrar deneyin."
    
    def chat_with_history(self, messages: list, model: str = None) -> str:
        """
        Chat with conversation history
        
        Args:
            messages: Full conversation history
            model: Model to use (if None, will use model rotation)
            
        Returns:
            AI response as string
        """
        try:
            response = self.make_chat_request(messages, model)
            
            # Check if response contains an error
            if "error" in response:
                return response["error"]
            
            return response["choices"][0]["message"]["content"]
            
        except Exception as e:
            logger.error(f"Error in chat with history: {e}")
            return f"Üzgünüm, şu anda teknik bir sorun yaşıyorum. Lütfen daha sonra tekrar deneyin."


def test_openrouter():
    """
    Test function for OpenRouter API
    """
    print("🤖 SidrexGPT - OpenRouter AI Test Starting...")
    print("=" * 50)
    
    # Initialize handler
    ai_handler = OpenRouterAIHandler()
    
    # Test 1: Get available models
    print("\n📋 Available Models:")
    try:
        models = ai_handler.get_available_models()
        free_models = [model for model in models.get('data', []) if 'free' in model.get('id', '').lower()]
        print(f"Total models: {len(models.get('data', []))}")
        print(f"Free models found: {len(free_models)}")
        if free_models:
            print("Some free models:")
            for model in free_models[:3]:
                print(f"  - {model.get('id', 'Unknown')}")
    except Exception as e:
        print(f"Error getting models: {e}")
    
    # Test 2: Simple question
    print("\n❓ Testing Simple Question:")
    question = "Merhaba! Sen kimsin?"
    print(f"Question: {question}")
    
    try:
        answer = ai_handler.ask_question(question)
        print(f"Answer: {answer}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 3: Question with system prompt
    print("\n🎭 Testing with System Prompt:")
    system_prompt = "Sen SidrexGPT'nin yardımcı yapay zeka asistanısın. Türkçe yanıt ver ve yardımcı ol."
    question2 = "Python programlama hakkında kısa bilgi verir misin?"
    
    try:
        answer2 = ai_handler.ask_question(question2, system_prompt=system_prompt)
        print(f"Question: {question2}")
        print(f"Answer: {answer2}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 4: Conversation history
    print("\n💬 Testing Conversation History:")
    conversation = [
        {"role": "system", "content": "Sen yardımcı bir AI asistanısın."},
        {"role": "user", "content": "Merhaba, adım Ahmet."},
        {"role": "assistant", "content": "Merhaba Ahmet! Size nasıl yardımcı olabilirim?"},
        {"role": "user", "content": "Benim adımı hatırlıyor musun?"}
    ]
    
    try:
        response = ai_handler.chat_with_history(conversation)
        print(f"AI Response: {response}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 OpenRouter AI Test Completed!")


def interactive_chat():
    """
    Interactive chat session with OpenRouter AI
    """
    print("🤖 SidrexGPT - Interactive Chat")
    print("Type 'quit' to exit")
    print("=" * 30)
    
    ai_handler = OpenRouterAIHandler()
    conversation = [
        {"role": "system", "content": "Sen SidrexGPT'nin yardımcı yapay zeka asistanısın. Türkçe yanıt ver, yardımcı ve samimi ol."}
    ]
    
    while True:
        try:
            user_input = input("\n👤 You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'çıkış']:
                print("👋 Hoşça kal!")
                break
            
            if not user_input:
                continue
            
            # Add user message to conversation
            conversation.append({"role": "user", "content": user_input})
            
            # Get AI response
            print("🤖 AI: ", end="", flush=True)
            ai_response = ai_handler.chat_with_history(conversation)
            print(ai_response)
            
            # Add AI response to conversation
            conversation.append({"role": "assistant", "content": ai_response})
            
        except KeyboardInterrupt:
            print("\n👋 Chat interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")


def main():
    """
    Main function
    """
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            test_openrouter()
        elif sys.argv[1] == "chat":
            interactive_chat()
        else:
            print("Usage: python ai-request.py [test|chat]")
    else:
        # Default: run test
        test_openrouter()


if __name__ == "__main__":
    main() 