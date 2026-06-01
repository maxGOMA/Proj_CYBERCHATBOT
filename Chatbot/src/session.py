from src.nlp_utils import clean_text

class Session:
    def __init__(self):
        self.history = []
        self.known_facts = []
        self.normalized_facts = set()
        self.last_intent = None
        self.last_threat = None
        self.last_confidence = 0.0
        self.last_evidence = []
        self.turn_count = 0
        self.long_case = False

    # añade un mensaje en el historial:
    def add_message(self, role, text):
        self.history.append((role, text))
        if role == "user":
            self.turn_count += 1

    # añade un nuevo valor en hechos conocidos si no estaba:
    def update_facts(self, text):
        normalized = clean_text(text)
        if normalized and normalized not in self.normalized_facts:
            self.normalized_facts.add(normalized)
            self.known_facts.append(text.strip())
            self.known_facts = self.known_facts[-8:]
            self.normalized_facts = {clean_text(item) for item in self.known_facts}

    # establece la intencion del usuario:
    def set_intent(self, intent):
        self.last_intent = intent

    # establece la amenaza encontrada:
    def set_threat(self, threat, confidence=0.0, evidence=None):
        self.last_threat = threat
        self.last_confidence = confidence
        self.last_evidence = list(evidence or [])

    def set_long_case(self, enabled):
        self.long_case = enabled

    def get_context(self):
        return {
            "turn_count": self.turn_count,
            "last_intent": self.last_intent,
            "last_threat": self.last_threat,
            "last_confidence": self.last_confidence,
            "last_evidence": self.last_evidence,
            "known_facts": self.known_facts,
            "long_case": self.long_case,
        }

    # guarda resultados externos pendientes de seleccion del usuario:
    def set_external_results(self, query, results):
        self.external_query = query
        self.external_results = results or []
        self.awaiting_external_choice = True

    # limpia el estado de seleccion externa:
    def clear_external_results(self):
        self.external_query = None
        self.external_results = []
        self.awaiting_external_choice = False

    # reset entero del sistema:
    def reset(self):
        self.__init__()
