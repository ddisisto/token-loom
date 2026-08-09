"""Generation, headless.

`gpt.gen` is already free of Tk and of the tree — it takes a prompt string and a
settings dict and returns a formatted response. So the spike wraps it rather than
reimplementing it, and inherits every provider quirk we've already paid for.

The one thing worth noting: generation here is an ordinary blocking call. The
tkinter app needs a worker thread and a hand-back queue because Tk owns the main
loop; a request handler does not. That entire class of problem disappears.
"""

import os
from copy import deepcopy

from gpt import gen
from model import DEFAULT_GENERATION_SETTINGS, DEFAULT_MODEL_CONFIG


def available_models():
    return sorted(DEFAULT_MODEL_CONFIG["models"].keys())


def default_settings():
    return deepcopy(DEFAULT_GENERATION_SETTINGS)


def _config():
    config = deepcopy(DEFAULT_MODEL_CONFIG)
    for entry in config["models"].values():
        # gpt.gen indexes api_base directly; not every stock entry defines it
        entry.setdefault("api_base", None)
    return config


def generate(prompt, settings):
    """Returns (response, error). Response is loom's formatted-response dict."""
    config = _config()
    model = settings.get("model")
    if model not in config["models"]:
        return None, f"unknown model {model!r}"
    if not prompt:
        # chat endpoints reject an empty message where the old completions API
        # tolerated it; fail here rather than burning a request to find out
        return None, "prompt is empty — write a seed before generating"

    response, error = gen(prompt, settings, config,
                          OPENROUTER_API_KEY=os.environ.get("OPENROUTER_API_KEY"))
    if error:
        return None, str(error)
    if not response or not response.get("completions"):
        return None, "no completions returned"
    return response, None
