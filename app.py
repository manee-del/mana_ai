from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)


def generate_prompt(feature, text):
    prompts = {
        "explain": f"Explain this concept in simple and clear terms:\n\n{text}",

        "summarize": f"Summarize the following text concisely:\n\n{text}",

        "rewrite": f"Rewrite the following text in a professional and polished manner:\n\n{text}",

        "bullet_points": f"Convert the following text into clear bullet points:\n\n{text}",

        "translate": f"Translate the following text into English:\n\n{text}"
    }

    return prompts.get(feature, text)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.get_json()

    user_text = data.get("text", "").strip()
    feature = data.get("feature", "explain")

    if not user_text:
        return jsonify({"error": "Input text cannot be empty."}), 400

    try:
        prompt = generate_prompt(feature, user_text)

        response = client.chat.completions.create(
            model="deepseek-r1:8b",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        return jsonify({
            "response": response.choices[0].message.content
        })

    except Exception as e:
        return jsonify({
            "error": f"Unable to connect to Ollama: {str(e)}"
        }), 500


if __name__ == "__main__":
    app.run(debug=True)