import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# nombres de los ficheros JSON por intencion:
INTENT_FILES = {
    "saludar":"saludar.json",
    "despedirse":"despedirse.json",
    "pedir_ayuda":"pedir_ayuda.json",
    "reportar_problema":"reportar_problema.json",
    "buscar_informacion":"buscar_informacion.json",
    "solicitar_recomendaciones":"solicitar_recomendaciones.json",
    "detectar_categoria":"detectar_categoria.json",
    "confirmar_negar":"confirmar_negar.json",
    "solicitar_pasos":"solicitar_pasos.json",
    "solicitar_diagnostico":"solicitar_diagnostico.json",
    "explicar_caso_largo":"explicar_caso_largo.json",
    "buenas_practicas":"buenas_practicas.json",
}

# carga y devuelve el dataset de una intencion concreta:
def load(intent_name):
    filename = INTENT_FILES.get(intent_name)
    if not filename:
        return {}
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# carga todos los datasets:
def load_all():
    all_data = {}
    for intent_name in INTENT_FILES:
        all_data[intent_name] = load(intent_name)
    return all_data


# devuelve solo los ejemplos de una intencion para construir el corpus:
def get_examples(intent_name):
    data = load(intent_name)
    return data.get("examples", [])


def all_intent_names():
    return list(INTENT_FILES.keys())


def build_examples_by_intent():
    examples_by_intent = {}

    for intent_name in INTENT_FILES:
        data = load(intent_name)
        examples = data.get("examples", [])

        if examples:
            examples_by_intent[intent_name] = examples
        else:
            examples_by_intent[intent_name] = []

    return examples_by_intent