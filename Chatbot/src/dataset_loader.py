import json
import os

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data"
)

INTENT_FILES = {
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
    "solicitar_respuesta_definitiva": "solicitar_respuesta_definitiva.json",
    "buenas_practicas": "buenas_practicas.json",
    "agradecer" : "agradecer.json",
    "listar_amenazas": "listar_amenazas.json"
}




def load(intent_name):
    filename = INTENT_FILES.get(intent_name)

    if filename is None:
        return {}

    path = os.path.join(DATA_DIR, filename)

    if os.path.exists(path) is False:
        return {}

    file = open(path, "r", encoding="utf-8")
    data = json.load(file)
    file.close()

    return data


def load_all():
    all_data = {}

    for intent_name in INTENT_FILES:
        all_data[intent_name] = load(intent_name)

    return all_data

def load_mobile_models():
    path = os.path.join(DATA_DIR, "modelos_moviles.json")

    if os.path.exists(path) is False:
        return {}

    file = open(path, "r", encoding="utf-8")
    data = json.load(file)
    file.close()

    return data

def get_examples(intent_name):
    data = load(intent_name)
    return data.get("examples", [])


def all_intent_names():
    return list(INTENT_FILES.keys())


def build_examples_by_intent():
    examples_by_intent = {}

    for intent_name in INTENT_FILES:
        examples_by_intent[intent_name] = get_examples(intent_name)

    return examples_by_intent