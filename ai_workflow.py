from ai_client import AIClient

class AIWorkflowManager:
    """
    Manages AI-powered text processing workflows.
    This class is responsible for building prompts and calling the AI client
    based on a specific action (e.g., 'improve', 'summarize').
    It is completely decoupled from the UI.
    """
    def __init__(self, ai_client: AIClient):
        self.ai_client = ai_client
        self.prompts = {
            "improve": "You are a writing assistant. Your task is to improve the clarity, grammar, and flow of the following text without changing its core meaning. Keep the tone professional and concise. The user's text is:",
            "academic": "You are an academic writing expert. Rewrite the following text in a formal, academic tone suitable for a research paper or thesis. Ensure the language is sophisticated, objective, and precise. The user's text is:",
            "expand": "You are a helpful assistant. Your task is to expand upon the following text. Add more detail, provide explanations, and give examples where appropriate to make the content more comprehensive. The user's text is:",
            "summarize": "You are a summarization expert. Your task is to create a concise summary of the following text, capturing the main points and key information. The user's text is:"
        }
        self.temperatures = {
            "improve": 0.3,
            "academic": 0.2,
            "expand": 0.6,
            "summarize": 0.3
        }

    def process(self, action_type: str, text: str):
        """
        Processes the given text based on the specified action.

        Args:
            action_type (str): The type of action to perform (e.g., 'improve').
            text (str): The text to process.

        Returns:
            dict: The result from the AI client, which includes 'success' and 'content' or 'error'.
        """
        if action_type not in self.prompts:
            return {"success": False, "error": f"Unknown action type: {action_type}"}

        # Build the full prompt
        system_prompt = self.prompts[action_type]
        full_prompt_text = f"{system_prompt}\n\n---\n\n{text}"
        
        # Prepare messages for the AI client
        messages = [{"role": "user", "content": full_prompt_text}]
        
        # Get the specific temperature for this action
        temperature = self.temperatures.get(action_type, 0.7) # Default to 0.7 if not found

        print(f"DEBUG: Processing AI action '{action_type}' with temperature {temperature}.")
        
        # Call the AI client
        return self.ai_client.get_completion(messages, temperature=temperature)
