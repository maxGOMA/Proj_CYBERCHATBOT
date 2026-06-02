import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import src.dataset_loader as dl
from src.inference_engine import (
    build_intent_model,
    detect_intent,
    INTENT_THRESHOLD,
)
from src.chatbot import Chatbot
from src.nlp_utils import clean_text

LABEL_MAP = {
    "phishing":"reportar_problema",
    "ransomware":"reportar_problema",
    "posible_incidente":"reportar_problema",
    "pedir_ayuda":"pedir_ayuda",
    "informacion_amenaza":"buscar_informacion",
    "listar_amenazas":"buscar_informacion",
    "recomendaciones_seguridad":"solicitar_recomendaciones",
    "saludo":"saludar",
    "salir":"despedirse",
}

def fallback_intent(text):
    clean = clean_text(text)
    if any(w in clean for w in ["hola", "buenas", "saludos"]):
        return "saludar"
    if any(w in clean for w in ["adios", "hasta luego", "chao"]):
        return "despedirse"
    if clean in {"si", "no", "vale", "correcto", "exacto", "ok"}:
        return "confirmar_negar"
    if "buenas practicas" in clean:
        return "buenas_practicas"
    if any(w in clean for w in ["paso", "pasos", "guia"]):
        return "solicitar_pasos"
    if any(w in clean for w in ["recomend", "proteg", "evitar", "prevenir"]):
        return "solicitar_recomendaciones"
    if any(w in clean for w in ["que es", "explicame", "informacion", "definicion"]):
        return "buscar_informacion"
    if any(w in clean for w in ["categoria", "tipo de ataque"]):
        return "detectar_categoria"
    if any(w in clean for w in ["ayuda", "menu", "opciones"]):
        return "pedir_ayuda"
    if len(clean.split()) >= 12:
        return "explicar_caso_largo"
    return "reportar_problema"


def run_evaluation():
    # 1. Cargar el test set
    with open("test.json", encoding="utf-8") as f:
        test_data = json.load(f)

    # 2. Construir el modelo de intenciones
    examples_by_intent = dl.build_examples_by_intent()
    intent_model = build_intent_model(examples_by_intent)

    # 3. Inferencia sobre cada muestra
    y_true, y_pred = [], []

    for sample in test_data:
        text       = sample["text"]
        true_label = LABEL_MAP.get(sample["intent"], sample["intent"])

        pred, score = detect_intent(text, intent_model)
        if score < INTENT_THRESHOLD:
            pred = fallback_intent(text)

        y_true.append(true_label)
        y_pred.append(pred)

    return y_true, y_pred, test_data


def compute_metrics(y_true, y_pred):
    from sklearn.metrics import (
        accuracy_score,
        precision_recall_fscore_support,
        confusion_matrix,
        classification_report,
    )

    classes = sorted(set(y_true))

    acc = accuracy_score(y_true, y_pred)
    prec, rec, f1, sup = precision_recall_fscore_support(
        y_true, y_pred, labels=classes, zero_division=0
    )
    cm = confusion_matrix(y_true, y_pred, labels=classes)

    print(f"\nAccuracy: {acc:.4f}  ({int(acc*len(y_true))}/{len(y_true)})\n")
    print(classification_report(y_true, y_pred, labels=classes, zero_division=0))

    return acc, classes, prec, rec, f1, sup, cm


def plot_metrics(classes, prec, rec, f1, sup, cm):
    import matplotlib.pyplot as plt
    import numpy as np
    from sklearn.metrics import ConfusionMatrixDisplay

    x = np.arange(len(classes))
    w = 0.25
    plt.figure(figsize=(10, 6))
    plt.bar(x - w, prec, w, label="Precision", color="#00d4a8")
    plt.bar(x, rec, w, label="Recall", color="#3b82f6")
    plt.bar(x + w, f1, w, label="F1-Score", color="#f59e0b")
    plt.xticks(x, classes, rotation=35, ha="right")
    plt.ylim(0, 1.05)
    plt.title("Precision · Recall · F1 por intención")
    plt.legend()
    plt.show()

    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=classes)
    fig, ax = plt.subplots(figsize=(8, 6))
    disp.plot(ax=ax, cmap="Blues", values_format='d')
    ax.set_title("Matriz de confusión")
    plt.show()

    plt.figure(figsize=(8, 4))
    plt.bar(classes, sup, color="#6b8aaa")
    plt.title("Support — muestras por intención")
    plt.xticks(rotation=35, ha="right")
    plt.show()


def print_errors(test_data, y_true, y_pred):
    print("\nErrores encontrados:")
    errors = []
    for i in range(len(y_true)):
        if y_true[i] != y_pred[i]:
            errors.append((test_data[i], y_true[i], y_pred[i]))


    for sample, true, pred in errors:
        print(f"  ✗ [{sample['intent']}]")
        print(f"    Texto  : {sample['text']}")
        print(f"    Esperado: {true}")
        print(f"    Predicho: {pred}\n")

    print(f"Total errores: {len(errors)} / {len(y_true)}")


if __name__ == "__main__":
    y_true, y_pred, test_data = run_evaluation()
    acc, classes, prec, rec, f1, sup, cm = compute_metrics(y_true, y_pred)
    print_errors(test_data, y_true, y_pred)
    plot_metrics(classes, prec, rec, f1, sup, cm)