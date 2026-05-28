class Session:
    def __init__(self):
        self.history     = []
        self.known_facts = []     
        self.last_intent = None
        self.last_threat = None
        self.turn_count  = 0
        self.long_case   = None
        self.external_query = None
        self.external_results = []
        self.awaiting_external_choice = False

    # añade un mensaje en el historial:
    def add_message(self, role, text):
        self.history.append((role, text))
        if role == "user":
            self.turn_count += 1

    # añade un nuevo valor en hechos conocidos si no estaba:
    def update_facts(self, text):
        if text and text not in self.known_facts:
            self.known_facts.append(text)

    # establece la intencion del usuario:
    def set_intent(self, intent):
        self.last_intent = intent

    # establece la amenaza encontrada:
    def set_threat(self, threat):
        self.last_threat = threat

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

    # para obtener la situacion en la que esta la conversacion:
    def get_context(self):
        return {
            "turn_count":  self.turn_count,
            "last_intent": self.last_intent,
            "last_threat": self.last_threat,
            "known_facts": self.known_facts,
            "long_case":   self.long_case,
        }

    # reset entero del sistema:
    def reset(self):
        self.__init__()
