from models.config import MODELS, DEFAULT_MODEL
from models.ollama_model import predict_ollama
from models.opus_model import predict_opus


def predict(text, model_key=None):
    if model_key is None:
        model_key = DEFAULT_MODEL

    if model_key not in MODELS:
        raise ValueError(f"Unknown model: {model_key}")

    model_info = MODELS[model_key]
    model_type = model_info["type"]
    model_name = model_info["name"]

    if model_type == "ollama":
        return predict_ollama(text, model_name)

    elif model_type == "anthropic":
        return predict_opus(text, model_name)

    else:
        raise ValueError(f"Unsupported model type: {model_type}")