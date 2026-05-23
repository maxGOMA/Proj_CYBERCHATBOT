import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import src.dataset_loader as dl
from src.nlp_utils       import full_pipeline, compute_idf, detect_intent
from src.inference_engine import InferenceEngine
from src.chatbot          import Chatbot

# entreno al chatbot con ejemplos para que pueda detectar problemas:
def build_corpus_and_idf():
    corpus = []

    # ejemplos de intenciones:
    for intent in dl.all_intent_names():
        for example in dl.get_examples(intent):
            corpus.append(full_pipeline(example))

    # sintomas de amenazas:
    ds_rep = dl.load("reportar_problema")
    for threat_data in ds_rep.get("threats", {}).values():
        for s in threat_data.get("symptoms", []):
            corpus.append(full_pipeline(s.get("term", "")))

    # keywords del dataset de informacion
    ds_info = dl.load("buscar_informacion")
    for threat_data in ds_info.get("threats", {}).values():
        for kw in threat_data.get("keywords", []):
            corpus.append(full_pipeline(kw))

    idf = compute_idf(corpus)
    return idf

# para comparar contra el input del usuario:
def build_intents_corpus(idf):
    intents_corpus = {}
    for intent in dl.all_intent_names():
        lemmas = []
        for example in dl.get_examples(intent):
            lemmas.extend(full_pipeline(example))
        intents_corpus[intent] = lemmas
    return intents_corpus


def main():
    print("Iniciando CyberBot, cargando modelos NLP...")

    # 1. Construir IDF global
    idf = build_corpus_and_idf()

    # 2. Construir corpus de intenciones
    intents_corpus = build_intents_corpus(idf)

    # 3. Función detectora de intenciones
    def intent_detector(user_text):
        return detect_intent(user_text, intents_corpus, idf)

    # 4. Motor de inferencia
    engine = InferenceEngine(idf=idf)

    # 5. Chatbot
    bot = Chatbot(
        intent_detector=intent_detector,
        inference_engine=engine,
        idf=idf
    )

    # 6. Arrancar
    bot.run()

main()