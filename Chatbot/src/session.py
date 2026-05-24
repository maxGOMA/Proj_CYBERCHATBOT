class Session:
    def __init__(self):
        self.history = []
        self.known_facts = []
        self.last_intent = None
        self.last_threat = None
        self.turn_count = 0
        self.long_case = False

    def add_message(self, role, text):
        self.history.append((role, text))
        if role == "user":
            self.turn_count += 1

    def update_facts(self, text):
        if text and text not in self.known_facts:
            self.known_facts.append(text)

    def set_intent(self, intent):
        self.last_intent = intent

    def set_threat(self, threat):
        self.last_threat = threat

    def set_long_case(self, enabled):
        self.long_case = enabled

    def get_context(self):
        return {
            "turn_count": self.turn_count,
            "last_intent": self.last_intent,
            "last_threat": self.last_threat,
            "known_facts": self.known_facts,
            "long_case": self.long_case,
        }

    def reset(self):
        self.__init__()
