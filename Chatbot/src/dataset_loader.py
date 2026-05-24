import json
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent.parent / "data"

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


def _read_json(filename):
    if not filename:
        return {}

    path = DATA_DIR / filename
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


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
    return {intent: get_examples(intent) for intent in all_intent_names()}
