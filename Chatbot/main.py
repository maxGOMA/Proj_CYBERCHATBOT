import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import src.dataset_loader as dl
from src.chatbot import Chatbot
from src.inference_engine import build_intent_model


def main():
    print("Iniciando CyberBot...")

    examples_by_intent = dl.build_examples_by_intent()
    intent_model = build_intent_model(examples_by_intent)

    bot = Chatbot(intent_model)
    bot.run()


if __name__ == "__main__":
    main()
