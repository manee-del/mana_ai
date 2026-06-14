# mana_ai
# Mana AI

Mana AI is a lightweight AI-powered web application built with Flask and Ollama that enables users to interact with a locally hosted Large Language Model (DeepSeek-R1:8B). The application provides multiple text-processing utilities through a clean and user-friendly interface while ensuring privacy by running entirely on the user's machine.

## Features

* Explain a Concept – Get simple and easy-to-understand explanations.
* Summarize Text – Generate concise summaries from lengthy content.
* Rewrite Professionally – Improve the tone and professionalism of text.
* Convert to Bullet Points – Transform paragraphs into structured bullet points.
* Translate to English – Translate text into English.
* Conversation Memory – Maintains context during a chat session.
* Chat History Persistence – Stores chat history in the browser and restores it after page refresh.
* New Chat Functionality – Clears conversation history and starts a fresh session.
* Local AI Processing – No cloud API usage required.

## Tech Stack

### Backend

* Python
* Flask
* OpenAI Python SDK (used with Ollama)

### Frontend

* HTML
* CSS
* JavaScript
* Marked.js (Markdown Rendering)

### AI Model

* DeepSeek-R1:8B
* Ollama

## Project Structure

```text
mana_ai/
│
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
│
└── templates/
    └── index.html
```

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/manee-del/mana_ai.git
cd mana_ai
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

Activate the environment:

#### Windows

```bash
venv\Scripts\activate
```

#### Linux / macOS

```bash
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Ollama

Download and install Ollama from:

https://ollama.com

### 5. Download DeepSeek-R1:8B

```bash
ollama pull deepseek-r1:8b
```

### 6. Start Ollama

```bash
ollama serve
```

### 7. Run the Application

```bash
python app.py
```

Open the application in your browser:

```text
http://127.0.0.1:5000
```

## How It Works

1. The user enters text and selects a feature.
2. Flask receives the request and generates a task-specific prompt.
3. The prompt is sent to the locally running DeepSeek-R1:8B model through Ollama.
4. The model processes the request and returns a response.
5. The response is displayed in the web interface with Markdown formatting.
6. Chat history is stored locally in the browser for persistence across page refreshes.

## Screenshots
<img width="1790" height="1124" alt="Screenshot 2026-06-08 153505" src="https://github.com/user-attachments/assets/b0a0dc7c-b1e3-44f4-8b33-8fdd1a769e4e" />
<img width="2818" height="1616" alt="Screenshot 2026-06-08 153522" src="https://github.com/user-attachments/assets/4f15fbc0-3e70-4233-9f46-0b976f352dfd" />

## Future Enhancements

* Multiple language translation support
* Export chat history
* Dark mode
* Voice input and speech output
* Multiple local model selection
* Database-backed conversation storage

## Learning Outcomes

This project demonstrates:

* Integration of Large Language Models into web applications
* Building REST APIs using Flask
* Frontend and backend communication using Fetch API
* Local AI deployment using Ollama
* Chat history management and conversation memory
* User interface design using HTML, CSS, and JavaScript

## License

This project is developed for educational and learning purposes.
