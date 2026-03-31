"""Routage intelligent des modèles Claude — optimisation coûts."""


def select_model(task_type: str, text_length: int = 0) -> str:
    HAIKU = "claude-haiku-4-5-20251001"
    SONNET = "claude-sonnet-4-6"
    OPUS = "claude-opus-4-6"

    routing = {
        "calculator": HAIKU,
        "simple_qa": HAIKU,
        "translation": HAIKU,
        "analysis": SONNET,
        "diagnostic": SONNET,
        "contract": SONNET,
        "complex": OPUS,
    }

    model = routing.get(task_type, SONNET)
    if task_type == "contract" and text_length > 15000:
        model = OPUS
    return model
