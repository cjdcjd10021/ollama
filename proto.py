import json
import os
import threading
from llama_cpp import Llama
from flask import Flask, Response, stream_with_context, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # enable CORS for all routes

# llms tracks which models are loaded
llms = {}
lock = threading.Lock()


def load(model):
    with lock:
        if not os.path.exists(f"./models/{model}.bin"):
            return {"error": "The model does not exist."}
        if model not in llms:
            llms[model] = Llama(model_path=f"./models/{model}.bin")
    return None


def unload(model):
    with lock:
        if not os.path.exists(f"./models/{model}.bin"):
            return {"error": "The model does not exist."}
        llms.pop(model, None)
    return None


def generate(model, prompt):
    # auto load
    error = load(model)
    if error is not None:
        return error
    stream = llms[model](
        str(prompt),  # TODO: optimize prompt based on model
        max_tokens=4096,
        stop=["Q:", "\n"],
        echo=True,
        stream=True,
    )
    for output in stream:
        yield json.dumps(output)


def models():
    all_files = os.listdir("./models")
    bin_files = [
        file.replace(".bin", "") for file in all_files if file.endswith(".bin")
    ]
    return bin_files


@app.route("/load", methods=["POST"])
def load_route_handler():
    data = request.get_json()
    model = data.get("model")
    if not model:
        return Response("Model is required", status=400)
    error = load(model)
    if error is not None:
        return error
    return Response(status=204)


@app.route("/unload", methods=["POST"])
def unload_route_handler():
    data = request.get_json()
    model = data.get("model")
    if not model:
        return Response("Model is required", status=400)
    error = unload(model)
    if error is not None:
        return error
    return Response(status=204)


@app.route("/generate", methods=["POST"])
def generate_route_handler():
    data = request.get_json()
    model = data.get("model")
    prompt = data.get("prompt")
    if not model:
        return Response("Model is required", status=400)
    if not prompt:
        return Response("Prompt is required", status=400)
    if not os.path.exists(f"./models/{model}.bin"):
        return {"error": "The model does not exist."}, 400
    return Response(
        stream_with_context(generate(model, prompt)), mimetype="text/event-stream"
    )


@app.route("/models", methods=["GET"])
def models_route_handler():
    bin_files = models()
    return Response(json.dumps(bin_files), mimetype="application/json")


if __name__ == "__main__":
    app.run(debug=True, threaded=True, port=5001)
    app.run()