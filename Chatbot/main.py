import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import src.dataset_loader as dl
from src.chatbot import Chatbot
from src.inference_engine import InferenceEngine
from src.nlp_utils import ExampleIntentDetector


def main():
    print("Iniciando CyberBot, cargando datasets NLP...")

    intent_detector = ExampleIntentDetector(dl.build_examples_by_intent())
    inference_engine = InferenceEngine()
    bot = Chatbot(intent_detector=intent_detector, inference_engine=inference_engine)
    bot.run()


if __name__ == "__main__":
    main()
