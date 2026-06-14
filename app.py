from datetime import datetime
from uuid import uuid4

from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "deepseek-r1:8b"

client = OpenAI(
    base_url=f"{OLLAMA_BASE_URL}/v1",
    api_key="ollama"
)

llm_messages_by_model = {}
chat_history = []

FEATURE_LABELS = {
    "explain": "Explain Concept",
    "eli5": "Explain Like I'm 5",
    "summarize": "Summarize Text",
    "rewrite": "Rewrite Pro",
    "bullet_points": "Bullet Points",
    "translate": "Translate"
}


def generate_prompt(feature, text):
    prompts = {
        "explain": (
            f"You are a knowledgeable and clear teacher. Your task is to explain the following "
            f"concept in a way that is easy to understand for someone encountering it for the first time.\n\n"
            f"Guidelines:\n"
            f"- Break down complex ideas into simple, digestible parts.\n"
            f"- Use real-world analogies or examples where helpful.\n"
            f"- Define any technical terms you use.\n"
            f"- Keep the tone friendly, informative, and engaging.\n"
            f"- Structure your explanation with a brief intro, the core explanation, and a takeaway.\n\n"
            f"Concept to explain:\n{text}"
        ),

        "eli5": (
            f"You are explaining something to a 5-year-old child. Use the simplest words possible, "
            f"very short sentences, and fun everyday comparisons a young child would instantly get.\n\n"
            f"Guidelines:\n"
            f"- No technical jargon whatsoever.\n"
            f"- Use comparisons to toys, food, animals, or everyday family life.\n"
            f"- Keep sentences short and punchy.\n"
            f"- Be warm, playful, and enthusiastic.\n"
            f"- End with a fun one-liner that wraps it all up.\n\n"
            f"Topic to explain:\n{text}"
        ),

        "summarize": (
            f"You are an expert at distilling information. Read the following text carefully and "
            f"produce a clear, accurate summary.\n\n"
            f"Guidelines:\n"
            f"- Capture all key ideas and important details.\n"
            f"- Remove filler, repetition, and minor details.\n"
            f"- Keep the summary roughly 20-30% of the original length.\n"
            f"- Maintain the original tone (formal stays formal, casual stays casual).\n"
            f"- Write in complete sentences and coherent paragraphs.\n\n"
            f"Text to summarize:\n{text}"
        ),

        "rewrite": (
            f"You are a professional editor and writing coach. Rewrite the following text so it sounds "
            f"polished, confident, and professional.\n\n"
            f"Guidelines:\n"
            f"- Fix grammar, punctuation, and spelling errors.\n"
            f"- Improve sentence structure and flow.\n"
            f"- Replace weak or vague words with precise, strong alternatives.\n"
            f"- Keep the original meaning and intent fully intact.\n"
            f"- Do not add new information or remove key points.\n"
            f"- Match a professional but approachable tone.\n\n"
            f"Text to rewrite:\n{text}"
        ),

        "bullet_points": (
            f"You are a precise and organized note-taker. Convert the following text into well-structured "
            f"bullet points that are easy to scan and understand.\n\n"
            f"Guidelines:\n"
            f"- Each bullet should represent one clear, standalone idea.\n"
            f"- Keep each bullet concise — ideally one sentence.\n"
            f"- Use sub-bullets for supporting details where needed.\n"
            f"- Preserve all important information from the original text.\n"
            f"- Order bullets logically (chronological, importance, or as they appear).\n"
            f"- Do not add information that isn't in the original text.\n\n"
            f"Text to convert:\n{text}"
        ),

        "translate": (
            f"You are a fluent, accurate translator. Translate the following text into English.\n\n"
            f"Guidelines:\n"
            f"- Preserve the original meaning as closely as possible.\n"
            f"- Keep the tone and register of the original (formal stays formal, casual stays casual).\n"
            f"- Do not add explanations, notes, or commentary — only the translated text.\n"
            f"- If a phrase has no direct English equivalent, use the closest natural equivalent.\n"
            f"- Ensure the translation reads naturally to a native English speaker.\n\n"
            f"Text to translate:\n{text}"
        ),
    }

    return prompts.get(feature, text)


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


def create_history_item(feature, user_text, assistant_response, model):
    return {
        "id": str(uuid4()),
        "feature": feature,
        "feature_label": FEATURE_LABELS.get(feature, "Custom Prompt"),
        "model": model,
        "user_text": user_text,
        "assistant_response": assistant_response,
        "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z"
    }


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/history", methods=["GET"])
def get_history():
    return jsonify({
        "history": chat_history
    })


@app.route("/api/models", methods=["GET"])
def get_models():
    try:
        models = get_available_models()

        return jsonify({
            "models": models,
            "default_model": resolve_model(),
            "error": None
        })

    except Exception as e:
        return jsonify({
            "models": [],
            "default_model": DEFAULT_MODEL,
            "error": f"Unable to load Ollama models: {str(e)}"
        }), 503


@app.route("/api/generate", methods=["POST"])
def generate():

    data = request.get_json(silent=True) or {}

    user_text = data.get("text", "").strip()
    feature = data.get("feature", "explain")
    requested_model = data.get("model", "").strip()

    if not user_text:
        return jsonify({
            "error": "Input text cannot be empty."
        }), 400

    if feature not in FEATURE_LABELS:
        return jsonify({
            "error": f"Invalid feature '{feature}'. Valid options are: {', '.join(FEATURE_LABELS.keys())}"
        }), 400

    try:
        selected_model = resolve_model(requested_model)
        prompt = generate_prompt(feature, user_text)
        model_messages = llm_messages_by_model.setdefault(selected_model, [])

        model_messages.append({
            "role": "user",
            "content": prompt
        })

        response = client.chat.completions.create(
            model=selected_model,
            messages=model_messages
        )

        assistant_response = response.choices[0].message.content

        model_messages.append({
            "role": "assistant",
            "content": assistant_response
        })

        history_item = create_history_item(
            feature,
            user_text,
            assistant_response,
            selected_model
        )
        chat_history.append(history_item)

        return jsonify({
            "response": assistant_response,
            "history_item": history_item
        })

    except Exception as e:
        return jsonify({
            "error": f"Unable to connect to Ollama: {str(e)}"
        }), 500


@app.route("/api/clear", methods=["POST"])
def clear_chat():
    global llm_messages_by_model, chat_history
    llm_messages_by_model = {}
    chat_history = []
    return jsonify({
        "message": "Chat cleared"
    })


if __name__ == "__main__":
    app.run(debug=True)