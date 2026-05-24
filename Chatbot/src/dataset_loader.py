import json
from functools import lru_cache
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
BROKEN_TEXT_MARKERS = ("Ã", "Â", "â", "\ufffd")

RUNTIME_FILES = {
    "saludar": "saludar.json",
    "despedirse": "despedirse.json",
    "pedir_ayuda": "pedir_ayuda.json",
    "reportar_problema": "reportar_problema.json",
    "buscar_informacion": "buscar_informacion.json",
    "solicitar_recomendaciones": "solicitar_recomendaciones.json",
    "detectar_categoria": "detectar_categoria.json",
    "confirmar_negar": "confirmar_negar.json",
    "solicitar_pasos": "solicitar_pasos.json",
    "solicitar_diagnostico": "solicitar_diagnostico.json",
    "explicar_caso_largo": "explicar_caso_largo.json",
    "buenas_practicas": "buenas_practicas.json",
}

TRAINING_FILES = {
    "saludar": "dataset_saludar.json",
    "despedirse": "dataset_despedirse.json",
    "pedir_ayuda": "dataset_pedir_ayuda.json",
    "reportar_problema": "dataset_reportar_problema.json",
    "buscar_informacion": "dataset_buscar_informacion.json",
    "solicitar_recomendaciones": "dataset_solicitar_recomendaciones.json",
    "detectar_categoria": "dataset_detectar_categoria.json",
    "confirmar_negar": "dataset_confirmar_negar.json",
    "solicitar_pasos": "dataset_solicitar_pasos.json",
    "solicitar_diagnostico": "dataset_solicitar_diagnostico.json",
    "explicar_caso_largo": "dataset_explicar_caso.json",
    "buenas_practicas": "dataset_buenas_practicas.json",
}


def _dedupe(items):
    seen = set()
    ordered = []

    for item in items:
        if not item or item in seen:
            continue

        seen.add(item)
        ordered.append(item)

    return ordered


def _repair_text(text):
    if not isinstance(text, str):
        return text

    if not any(marker in text for marker in BROKEN_TEXT_MARKERS):
        return text

    try:
        repaired = text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text

    return repaired


def _repair_value(value):
    if isinstance(value, dict):
        return {key: _repair_value(item) for key, item in value.items()}

    if isinstance(value, list):
        return [_repair_value(item) for item in value]

    if isinstance(value, str):
        return _repair_text(value)

    return value


@lru_cache(maxsize=None)
def _read_json(filename):
    if not filename:
        return {}

    path = DATA_DIR / filename
    with path.open("r", encoding="utf-8") as file:
        return _repair_value(json.load(file))


def load(intent_name):
    return _read_json(RUNTIME_FILES.get(intent_name))


def load_training(intent_name):
    return _read_json(TRAINING_FILES.get(intent_name))


def load_all():
    return {intent: load(intent) for intent in RUNTIME_FILES}


def load_all_training():
    return {intent: load_training(intent) for intent in TRAINING_FILES}


def get_examples(intent_name):
    return load_training(intent_name).get("examples", [])


def all_intent_names():
    return list(TRAINING_FILES.keys())


def build_examples_by_intent():
    examples_by_intent = {}
    runtime_data = load_all()

    for intent in all_intent_names():
        examples = []
        training_data = load_training(intent)
        runtime_intent_data = runtime_data.get(intent, {})

        examples.extend(training_data.get("examples", []))
        examples.extend(runtime_intent_data.get("examples", []))

        if intent == "reportar_problema":
            for threat_name, threat_data in runtime_intent_data.get("threats", {}).items():
                examples.append(threat_name.replace("_", " "))
                examples.append("tengo " + threat_name.replace("_", " "))
                examples.extend(
                    symptom.get("term", "") for symptom in threat_data.get("symptoms", [])
                )

        if intent == "buscar_informacion":
            for threat_name, threat_data in runtime_intent_data.get("threats", {}).items():
                title = threat_data.get("title", threat_name.replace("_", " "))
                examples.append("que es " + title)
                examples.append("explicame " + title)
                examples.extend(threat_data.get("keywords", []))

        if intent == "solicitar_recomendaciones":
            for threat_name in runtime_intent_data.get("by_threat", {}):
                readable_name = threat_name.replace("_", " ")
                examples.append("como me protejo de " + readable_name)
                examples.append("recomendaciones para " + readable_name)

        if intent == "solicitar_pasos":
            for threat_name in runtime_intent_data.get("steps", {}):
                readable_name = threat_name.replace("_", " ")
                examples.append("pasos para " + readable_name)
                examples.append("como resolver " + readable_name)

        examples_by_intent[intent] = _dedupe(examples)

    return examples_by_intent
