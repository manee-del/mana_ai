import ast
import json
import math
import operator
import os
import re
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import requests
from flask import Flask, jsonify, render_template, request
from openai import OpenAI


app = Flask(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "deepseek-r1:8b")
MEMORY_PATH = Path("data") / "agent_memory.json"

client = OpenAI(base_url=f"{OLLAMA_BASE_URL}/v1", api_key="ollama")

AGENT_MODES = {
    "project_mentor": {
        "label": "AI Project Mentor",
        "description": "Turns a rough AI project idea into an implementation plan, risks, and next steps.",
        "icon": "route",
    },
    "startup_validator": {
        "label": "Startup Validator",
        "description": "Checks a startup idea for users, competition, feasibility, and launch strategy.",
        "icon": "rocket",
    },
    "research_agent": {
        "label": "Research Agent",
        "description": "Researches a topic, compares evidence, and produces a sourced briefing.",
        "icon": "search",
    },
    "travel_planner": {
        "label": "Travel Planner",
        "description": "Builds an itinerary using preferences, rough budgets, and practical constraints.",
        "icon": "map",
    },
    "resume_reviewer": {
        "label": "Resume Reviewer",
        "description": "Reviews resume text against a target role and recommends concrete improvements.",
        "icon": "file-user",
    },
}

chat_history = []


def utc_now():
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def ensure_memory_file():
    MEMORY_PATH.parent.mkdir(exist_ok=True)
    if not MEMORY_PATH.exists():
        MEMORY_PATH.write_text(json.dumps({"memories": [], "sessions": []}, indent=2), encoding="utf-8")


def load_memory_store():
    ensure_memory_file()
    try:
        return json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"memories": [], "sessions": []}


def save_memory_store(store):
    ensure_memory_file()
    MEMORY_PATH.write_text(json.dumps(store, indent=2), encoding="utf-8")


def tokenize(text):
    return set(re.findall(r"[a-zA-Z0-9]+", (text or "").lower()))


def retrieve_memories(query, limit=4):
    store = load_memory_store()
    query_terms = tokenize(query)
    scored = []

    for memory in store.get("memories", []):
        haystack = " ".join([
            memory.get("user_input", ""),
            memory.get("summary", ""),
            memory.get("mode", ""),
            " ".join(memory.get("tags", [])),
        ])
        overlap = len(query_terms & tokenize(haystack))
        if overlap:
            scored.append((overlap, memory))

    scored.sort(key=lambda item: (item[0], item[1].get("created_at", "")), reverse=True)
    return [memory for _, memory in scored[:limit]]


def remember_interaction(mode, user_input, answer, tool_results):
    store = load_memory_store()
    compact_answer = re.sub(r"\s+", " ", answer or "").strip()[:650]
    tags = sorted(list(tokenize(user_input)))[:10]

    store.setdefault("memories", []).append({
        "id": str(uuid4()),
        "created_at": utc_now(),
        "mode": mode,
        "user_input": user_input,
        "summary": compact_answer,
        "tools_used": [result["tool"] for result in tool_results],
        "tags": tags,
    })

    store["memories"] = store["memories"][-80:]
    save_memory_store(store)


def get_available_models():
    models = client.models.list()
    return sorted(model.id for model in models.data)


def resolve_model(requested_model=None):
    models = get_available_models()
    if requested_model and requested_model in models:
        return requested_model
    if DEFAULT_MODEL in models:
        return DEFAULT_MODEL
    if models:
        return models[0]
    return requested_model or DEFAULT_MODEL


def safe_calculate(expression):
    allowed_operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.Mod: operator.mod,
    }
    allowed_names = {
        "ceil": math.ceil,
        "floor": math.floor,
        "sqrt": math.sqrt,
        "round": round,
        "min": min,
        "max": max,
    }

    def evaluate(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in allowed_operators:
            return allowed_operators[type(node.op)](evaluate(node.left), evaluate(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in allowed_operators:
            return allowed_operators[type(node.op)](evaluate(node.operand))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in allowed_names:
            return allowed_names[node.func.id](*[evaluate(arg) for arg in node.args])
        raise ValueError("Only numbers, arithmetic operators, and simple math functions are allowed.")

    parsed = ast.parse(expression, mode="eval")
    return evaluate(parsed.body)


def extract_numbers(text):
    return [float(match) for match in re.findall(r"\b\d+(?:\.\d+)?\b", text or "")]


def calculator_tool(user_input, mode):
    numbers = extract_numbers(user_input)

    if "budget" in user_input.lower() or "travel" in mode:
        if len(numbers) >= 2:
            days, budget = numbers[0], numbers[1]
            expression = f"{budget} / {days}"
            result = safe_calculate(expression)
            return {
                "tool": "calculator",
                "title": "Daily budget estimate",
                "input": expression,
                "output": f"Estimated daily budget: {result:.2f}",
            }

    if "conversion" in user_input.lower() or "rate" in user_input.lower() or "%" in user_input:
        if len(numbers) >= 2:
            expression = f"({numbers[0]} * {numbers[1]}) / 100"
            result = safe_calculate(expression)
            return {
                "tool": "calculator",
                "title": "Percentage calculation",
                "input": expression,
                "output": f"{numbers[1]}% of {numbers[0]} is {result:.2f}",
            }

    score_seed = min(100, 45 + len(tokenize(user_input)) * 2 + len(numbers) * 5)
    return {
        "tool": "calculator",
        "title": "Feasibility score",
        "input": "Keyword and constraint scoring",
        "output": f"Initial feasibility signal: {score_seed}/100 based on specificity, constraints, and measurable details.",
    }


def web_search_tool(query):
    params = {
        "q": query,
        "format": "json",
        "no_html": 1,
        "skip_disambig": 1,
    }

    try:
        response = requests.get("https://api.duckduckgo.com/", params=params, timeout=8)
        response.raise_for_status()
        data = response.json()

        snippets = []
        if data.get("AbstractText"):
            snippets.append({
                "title": data.get("Heading") or "DuckDuckGo abstract",
                "snippet": data["AbstractText"],
                "url": data.get("AbstractURL") or "https://duckduckgo.com/",
            })

        for topic in data.get("RelatedTopics", [])[:4]:
            if isinstance(topic, dict) and topic.get("Text"):
                snippets.append({
                    "title": topic.get("FirstURL", "Related result"),
                    "snippet": topic["Text"],
                    "url": topic.get("FirstURL", "https://duckduckgo.com/"),
                })

        if not snippets:
            snippets.append({
                "title": "Search fallback",
                "snippet": "No instant-answer snippet was returned. Use the query as a research direction and verify externally.",
                "url": f"https://duckduckgo.com/?q={requests.utils.quote(query)}",
            })

        return {
            "tool": "web_search",
            "title": "Web research",
            "input": query,
            "output": snippets,
        }
    except Exception as exc:
        return {
            "tool": "web_search",
            "title": "Web research",
            "input": query,
            "output": [{
                "title": "Search unavailable",
                "snippet": f"Live search failed: {exc}. The agent will continue using the provided brief and memory.",
                "url": "",
            }],
            "error": True,
        }


def memory_tool(user_input):
    memories = retrieve_memories(user_input)
    return {
        "tool": "memory",
        "title": "Long-term memory lookup",
        "input": user_input,
        "output": memories or [{
            "summary": "No prior matching memory found. This interaction will become future memory.",
            "created_at": utc_now(),
            "mode": "new_session",
        }],
    }


def build_plan(mode, user_input):
    label = AGENT_MODES.get(mode, AGENT_MODES["project_mentor"])["label"]
    steps = [
        {
            "step": "Understand the user's goal and constraints",
            "tool": "planner",
            "reason": f"Frame the request as a {label} workflow before taking action.",
        },
        {
            "step": "Retrieve relevant previous context",
            "tool": "memory",
            "reason": "Personal memory lets the agent adapt recommendations across sessions.",
        },
    ]

    needs_research = mode in {"research_agent", "startup_validator", "travel_planner", "project_mentor"}
    if needs_research:
        steps.append({
            "step": "Collect external context",
            "tool": "web_search",
            "reason": "Fresh outside information helps avoid a generic answer.",
        })

    steps.append({
        "step": "Quantify feasibility, budget, or priority",
        "tool": "calculator",
        "reason": "A numerical signal makes the recommendation easier to compare and act on.",
    })
    steps.append({
        "step": "Synthesize a final recommendation",
        "tool": "llm",
        "reason": "The LLM combines the plan, memory, research, and calculations into a useful response.",
    })
    return steps


def run_tools(mode, user_input, plan):
    tool_results = []

    if any(step["tool"] == "memory" for step in plan):
        tool_results.append(memory_tool(user_input))

    if any(step["tool"] == "web_search" for step in plan):
        search_query = f"{AGENT_MODES.get(mode, AGENT_MODES['project_mentor'])['label']} {user_input}"
        tool_results.append(web_search_tool(search_query[:240]))

    if any(step["tool"] == "calculator" for step in plan):
        tool_results.append(calculator_tool(user_input, mode))

    return tool_results


def tool_results_as_text(tool_results):
    lines = []
    for result in tool_results:
        lines.append(f"Tool: {result['tool']} | {result['title']}")
        lines.append(f"Input: {result['input']}")
        output = result["output"]
        if isinstance(output, list):
            for item in output[:5]:
                if "snippet" in item:
                    lines.append(f"- {item.get('title')}: {item.get('snippet')} ({item.get('url')})")
                else:
                    lines.append(f"- {item.get('created_at')}: {item.get('summary')}")
        else:
            lines.append(f"- {output}")
    return "\n".join(lines)


def synthesize_response(mode, user_input, plan, tool_results, model):
    label = AGENT_MODES.get(mode, AGENT_MODES["project_mentor"])["label"]
    system_prompt = (
        "You are Mana Agent, an autonomous AI assistant. Use the supplied plan and tool outputs. "
        "Be practical, specific, and honest about uncertainty. Do not invent sources. "
        "Format with concise markdown headings and action-oriented bullets."
    )
    user_prompt = f"""
Agent mode: {label}
User request:
{user_input}

Plan:
{json.dumps(plan, indent=2)}

Tool evidence:
{tool_results_as_text(tool_results)}

Write the final answer with:
1. A short diagnosis of the situation.
2. The recommendation or plan.
3. Evidence from tools and why each tool mattered.
4. Concrete next actions.
"""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
        max_tokens=700,
    )
    answer = (response.choices[0].message.content or "").strip()
    if answer:
        return answer
    return fallback_synthesis(mode, user_input, plan, tool_results)


def fallback_synthesis(mode, user_input, plan, tool_results):
    label = AGENT_MODES.get(mode, AGENT_MODES["project_mentor"])["label"]
    calculator = next((item for item in tool_results if item["tool"] == "calculator"), None)
    memory = next((item for item in tool_results if item["tool"] == "memory"), None)
    search = next((item for item in tool_results if item["tool"] == "web_search"), None)
    score = calculator["output"] if calculator else "No numeric signal was available."
    memory_note = "No matching prior memory was found."

    if memory and isinstance(memory["output"], list) and memory["output"]:
        memory_note = memory["output"][0].get("summary", memory_note)

    search_note = "Live research did not return a usable snippet."
    if search and isinstance(search["output"], list) and search["output"]:
        search_note = search["output"][0].get("snippet", search_note)

    plan_lines = "\n".join([f"- {item['step']} using `{item['tool']}`" for item in plan])
    return f"""## {label} Result

The request is specific enough for an agentic pass: {user_input}

## Recommendation

Treat this as a focused MVP. Keep the first version narrow, test it with a small group of real users, and avoid building advanced features until the core workflow proves useful.

## Tool Evidence

- Memory: {memory_note}
- Web search: {search_note}
- Calculator: {score}

## Agent Plan Used

{plan_lines}

## Next Actions

1. Define one target user and one measurable success metric.
2. Build the smallest workflow that produces a useful result.
3. Test with 3-5 users and collect the failure cases.
4. Use the feedback to decide whether to continue, pivot, or stop.
"""


def create_history_item(mode, user_text, assistant_response, model, plan, tool_results):
    return {
        "id": str(uuid4()),
        "mode": mode,
        "mode_label": AGENT_MODES.get(mode, AGENT_MODES["project_mentor"])["label"],
        "model": model,
        "user_text": user_text,
        "assistant_response": assistant_response,
        "plan": plan,
        "tool_results": tool_results,
        "created_at": utc_now(),
    }


@app.route("/")
def home():
    return render_template("index.html", modes=AGENT_MODES)


@app.route("/api/history", methods=["GET"])
def get_history():
    return jsonify({"history": chat_history})


@app.route("/api/memory", methods=["GET"])
def get_memory():
    store = load_memory_store()
    return jsonify({"memories": store.get("memories", [])[-20:]})


@app.route("/api/models", methods=["GET"])
def get_models():
    try:
        models = get_available_models()
        return jsonify({"models": models, "default_model": resolve_model(), "error": None})
    except Exception as exc:
        return jsonify({
            "models": [],
            "default_model": DEFAULT_MODEL,
            "error": f"Unable to load Ollama models: {exc}",
        }), 503


@app.route("/api/agent", methods=["POST"])
def run_agent():
    data = request.get_json(silent=True) or {}
    user_text = data.get("text", "").strip()
    mode = data.get("mode", "project_mentor").strip()
    requested_model = data.get("model", "").strip()

    if not user_text:
        return jsonify({"error": "Describe the problem you want the agent to solve."}), 400
    if mode not in AGENT_MODES:
        return jsonify({"error": f"Invalid agent mode '{mode}'."}), 400

    try:
        selected_model = resolve_model(requested_model)
        plan = build_plan(mode, user_text)
        tool_results = run_tools(mode, user_text, plan)
        assistant_response = synthesize_response(mode, user_text, plan, tool_results, selected_model)
        remember_interaction(mode, user_text, assistant_response, tool_results)
        history_item = create_history_item(mode, user_text, assistant_response, selected_model, plan, tool_results)
        chat_history.append(history_item)
        return jsonify({"response": assistant_response, "history_item": history_item})
    except Exception as exc:
        return jsonify({"error": f"Agent run failed: {exc}"}), 500


@app.route("/api/clear", methods=["POST"])
def clear_chat():
    global chat_history
    chat_history = []
    return jsonify({"message": "Chat history cleared. Long-term memory is preserved."})


@app.route("/api/clear-memory", methods=["POST"])
def clear_memory():
    save_memory_store({"memories": [], "sessions": []})
    return jsonify({"message": "Long-term memory cleared."})


if __name__ == "__main__":
    ensure_memory_file()
    app.run(debug=True)