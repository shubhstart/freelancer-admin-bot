# Hallucination Hunters --- Freelancer Admin (FREE VERSION)

This version of the project is modified to run **without an OpenAI API Key** by using local LLMs via **Ollama**.

## How to Run for Free

1. **Install Ollama**: Download and install from [ollama.com](https://ollama.com).
2. **Pull the Model**: Open your terminal and run:
   ```bash
   ollama pull llama3.2
   ```
   *(Note: You can use other models by updating LLM_MODEL in API.txt)*
3. **Start Ollama**: Make sure the Ollama application is running.
4. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
5. **Run the App**:
   ```bash
   python app.py
   ```

The application will now connect to `http://localhost:11434/v1` and use the local model for all intent detection and agent tasks.

## Configuration (Optional)
You can modify `API.txt` to change the local model name or the base URL. If you want to switch back to OpenAI, set `USE_OPENAI=true` in your environment and provide a key in `API.txt`.

## Features
- **Local & Private**: No data leaves your machine.
- **Cost-free**: No tokens to pay for.
- **Multilingual Support**: Still supports Hindi, Tamil, Kannada, and Marathi (model quality may vary).
