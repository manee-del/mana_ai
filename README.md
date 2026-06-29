# Mana Agent

Mana Agent is an agentic AI web application built with Flask, a polished HTML/CSS/JavaScript frontend, and a local LLM served through Ollama's OpenAI-compatible API. It is designed for Task 5: building an AI application that goes beyond a basic chatbot by planning, selecting tools, using memory, and completing multi-step workflows.

## What I Built

Mana Agent helps users solve real-world planning and decision problems through different agent modes:

- AI Project Mentor
- Startup Idea Validator
- Research Agent
- Travel Planning Agent
- Resume Review Agent

The user enters a problem, chooses an agent mode, and selects a local Ollama model. The app then shows the agent plan, tool calls, memory lookup, and final recommendation in the interface.

## Agent Workflow

The application follows this workflow:

1. User submits a real-world request.
2. The backend creates a task plan based on the selected agent mode.
3. The agent retrieves relevant long-term memories from previous sessions.
4. The agent runs external tools such as web research and calculation.
5. The LLM receives the plan plus tool evidence.
6. The LLM synthesizes a final response with recommendations and next actions.
7. The app saves a compact memory of the interaction for future sessions.

This makes the system agentic because it performs multiple autonomous steps before answering, instead of using a single prompt-response call.

## Tools Used

### 1. Web Search Tool

The app uses DuckDuckGo's instant-answer API through Python `requests`.

Why it is needed:

- Research, startup validation, and project mentoring require outside context.
- The tool gives the LLM external evidence instead of relying only on its model knowledge.
- If live search is unavailable, the app continues gracefully and reports the issue in the tool output.

### 2. Calculator Tool

The app includes a safe arithmetic calculator implemented with Python's `ast` module.

Why it is needed:

- Travel planning needs daily budget estimates.
- Startup and project validation benefit from simple feasibility scoring.
- Numeric reasoning is handled by a tool rather than trusting the LLM to calculate.

### 3. Memory Tool

The app searches saved memories from earlier interactions.

Why it is needed:

- The agent can adapt to repeated user preferences and previous project context.
- It demonstrates memory across interactions and sessions.
- The frontend displays the number of saved memories and lets the user clear memory.

## Memory Implementation

Long-term memory is stored in:

```text
data/agent_memory.json
```

Each saved memory includes:

- Timestamp
- Agent mode
- Original user request
- Compact answer summary
- Tools used
- Search tags

When a new request arrives, the app tokenizes the request, compares it with saved memory tags and summaries, and retrieves the most relevant memories. The memory file is created automatically the first time the app runs.

## Tech Stack

- Python
- Flask
- OpenAI Python SDK
- Ollama
- DuckDuckGo instant-answer API
- HTML
- CSS
- JavaScript
- Marked.js for markdown rendering
- Lucide icons

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Start Ollama and pull a model:

```bash
ollama pull deepseek-r1:8b
```

3. Run the Flask app:

```bash
python app.py
```

4. Open the app:

```text
http://127.0.0.1:5000
```

## Environment Variables

Optional settings:

```bash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=deepseek-r1:8b
```

## Demo Photos
<img width="1750" height="904" alt="image" src="https://github.com/user-attachments/assets/5e751f4f-510a-4d13-b0c1-233664bb275c" />

<img width="2806" height="1644" alt="image" src="https://github.com/user-attachments/assets/9254a818-772f-4814-8c8d-02a72e481f8a" />





## Why This Is Agentic

Mana Agent is not a simple chatbot. It demonstrates:

- User input
- LLM API usage through Ollama/OpenAI compatibility
- Multiple tools
- Persistent memory
- Multi-step workflow
- Planning and tool selection
- Autonomous synthesis of a final response
- A polished frontend that exposes the agent reasoning workflow
