import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.chatbot import Chatbot
from src.gui import CyberBotGUI


def build_bot():
    bot = Chatbot()
    return bot


def main():
    bot = build_bot()
    app = CyberBotGUI(bot)
    app.run()


if __name__ == "__main__":
    main()