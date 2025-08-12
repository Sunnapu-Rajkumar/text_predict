# server.py
import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

MODEL_NAME = os.getenv("MODEL_NAME", "distilgpt2")
model_loaded = False
text_generator = None

try:
    from transformers import pipeline
    logging.info(f"Loading HF model: {MODEL_NAME} (this can take time)...")
    text_generator = pipeline("text-generation", model=MODEL_NAME)
    model_loaded = True
    logging.info("Model loaded successfully.")
except Exception as e:
    logging.exception("Model load failed — server will run in fallback (dummy) mode.")

@app.route("/")
def home():
    return "Suggestion server up. POST /suggest with JSON {\"line\": \"...\"}"

@app.route("/suggest", methods=["POST"])
def suggest():
    data = request.get_json() or {}
    line = (data.get("line") or "").strip()
    if not line:
        return jsonify({"suggestion": ""})

    if model_loaded and text_generator is not None:
        try:
            # approximate token limit = words + new tokens
            max_new_tokens = min(max(20, len(line.split()) + 20), 200)
            # `max_length` is total tokens (approx). We'll approximate with words count + max_new_tokens
            max_length = len(line.split()) + max_new_tokens
            out = text_generator(
                line,
                max_length=max_length,
                do_sample=True,
                top_k=50,
                top_p=0.95,
                temperature=0.7,
                num_return_sequences=1,
            )
            generated = out[0]["generated_text"]
            suggestion = generated[len(line):].strip()
            # return only first line / sentence-like chunk
            suggestion = suggestion.split("\n")[0].strip()
            return jsonify({"suggestion": suggestion})
        except Exception as e:
            logging.exception("Error generating suggestion")
            return jsonify({"suggestion": "", "error": str(e)}), 500
    else:
        # fallback dummy suggestion (useful for testing or low-resource hosts)
        dummy = "lorem ipsum dolor sit amet, consectetur adipiscing elit."
        return jsonify({"suggestion": dummy})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    app.run(host="0.0.0.0", port=port, debug=False)
