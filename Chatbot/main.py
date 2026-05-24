import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import src.dataset_loader as dl
from src.chatbot import Chatbot
from src.inference_engine import build_info_model
from src.inference_engine import build_intent_model
from src.inference_engine import build_threat_model


def build_bot():
    examples_by_intent = dl.build_examples_by_intent()
    intent_model = build_intent_model(examples_by_intent)
    threat_model = build_threat_model(dl.load("reportar_problema"))
    info_model = build_info_model(dl.load("buscar_informacion"))
    return Chatbot(intent_model, threat_model=threat_model, info_model=info_model)


def main():
    bot = build_bot()

    if "--cli" in sys.argv:
        bot.run()
        return

    try:
        from src.gui import CyberBotGUI

        app = CyberBotGUI(bot)
        app.run()
    except Exception as error:
        print("No se pudo iniciar la interfaz grafica. Cambio a modo consola.")
        print("Motivo:", error)
        bot.run()


if __name__ == "__main__":
    main()
