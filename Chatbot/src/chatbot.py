import random

import src.dataset_loader as dl
from src.nlp_utils import normalize_text
from src.session import Session


THREAT_NAMES = {
    "phishing": "Phishing",
    "ransomware": "Ransomware",
    "ddos": "Ataque DDoS",
    "sql_injection": "Inyeccion SQL",
    "malware": "Malware / Virus",
    "man_in_the_middle": "Man-in-the-Middle",
    "brute_force": "Fuerza Bruta",
    "insider_threat": "Amenaza Interna",
}

INTENT_THRESHOLD = 0.12


class Chatbot:
    def __init__(self, intent_detector, inference_engine):
        self.detector = intent_detector
        self.engine = inference_engine
        self.session = Session()
        self.handlers = {
            "saludar": self.greet_handler,
            "despedirse": self.farewell_handler,
            "pedir_ayuda": self.help_handler,
            "reportar_problema": self.report_problem_handler,
            "buscar_informacion": self.information_request_handler,
            "solicitar_recomendaciones": self.recommendations_request_handler,
            "detectar_categoria": self.category_handler,
            "confirmar_negar": self.confirm_deny_handler,
            "solicitar_pasos": self.steps_to_follow_handler,
            "solicitar_diagnostico": self.report_problem_handler,
            "explicar_caso_largo": self.long_case_handler,
            "buenas_practicas": self.good_practices_handler,
        }

    def process_input(self, user_text):
        if not user_text.strip():
            return "No he recibido ningun texto. En que puedo ayudarte?"

        self.session.add_message("user", user_text)
        intent, score = self.detector(user_text)

        if not intent or score < INTENT_THRESHOLD:
            intent = self._fallback_intent(user_text)

        self.session.set_intent(intent)
        handler = self.handlers.get(intent, self.report_problem_handler)
        response = handler(user_text)
        self.session.add_message("bot", response)
        return response

    def greet_handler(self, _text):
        data = dl.load("saludar")
        return random.choice(data.get("responses", ["Hola. En que puedo ayudarte?"]))

    def farewell_handler(self, _text):
        data = dl.load("despedirse")
        return random.choice(data.get("responses", ["Hasta luego."]))

    def help_handler(self, _text):
        data = dl.load("pedir_ayuda")
        response = data.get("response", {})
        lines = [response.get("intro", "Puedo ayudarte con lo siguiente:")]

        for option in response.get("options", []):
            lines.append(f"  - {option}")

        return "\n".join(lines)

    def report_problem_handler(self, text):
        dataset = dl.load("reportar_problema")
        threat, score, all_scores = self.engine.evaluate(text, dataset)
        self.session.update_facts(text)

        if threat is None and len(self.session.known_facts) > 1:
            accumulated = self.engine.forward_chaining(self.session.known_facts, dataset)
            if accumulated:
                threat, score = next(iter(accumulated.items()))
                all_scores = accumulated

        if threat is None:
            return self.no_diagnosis()

        self.session.set_threat(threat)
        self.session.set_long_case(False)
        threat_data = dataset["threats"][threat]
        return self.format_diagnosis(threat, threat_data, score, all_scores)

    def information_request_handler(self, text):
        dataset = dl.load("buscar_informacion")
        threat = self.engine.find_in_info_dataset(text, dataset)

        if not threat and self.session.last_threat:
            threat = self.session.last_threat

        if not threat:
            return (
                "No he encontrado informacion sobre ese tema.\n"
                "Prueba con: 'que es el phishing', 'explicame el ransomware' o "
                "'que es un ataque DDoS'."
            )

        threat_data = dataset["threats"][threat]
        threat_name = THREAT_NAMES.get(threat, threat)
        lines = [
            threat_name,
            "",
            f"Resumen: {threat_data.get('summary', '')}",
            "",
            f"Detalle: {threat_data.get('detail', '')}",
            "",
            "Si quieres, tambien puedo darte recomendaciones o pasos de respuesta.",
        ]
        return "\n".join(lines)

    def recommendations_request_handler(self, text):
        recommendations = dl.load("solicitar_recomendaciones")
        report_dataset = dl.load("reportar_problema")
        threat, _, _ = self.engine.evaluate(text, report_dataset)

        if not threat:
            threat = self.session.last_threat

        if threat and threat in recommendations.get("by_threat", {}):
            threat_name = THREAT_NAMES.get(threat, threat)
            lines = [f"Recomendaciones para {threat_name}:"]

            for index, item in enumerate(recommendations["by_threat"][threat], start=1):
                lines.append(f"  {index}. {item}")

            return "\n".join(lines)

        general_tips = recommendations.get("general", [])
        lines = ["Buenas practicas generales:"]

        for index, item in enumerate(general_tips, start=1):
            lines.append(f"  {index}. {item}")

        return "\n".join(lines)

    def category_handler(self, text):
        category_dataset = dl.load("detectar_categoria")
        report_dataset = dl.load("reportar_problema")
        threat, _, _ = self.engine.evaluate(text, report_dataset)

        if not threat:
            threat = self.session.last_threat

        if not threat:
            return "No he identificado una amenaza concreta. Describe primero el problema."

        categories = category_dataset.get("categories", {})
        descriptions = category_dataset.get("category_descriptions", {})
        threat_name = THREAT_NAMES.get(threat, threat)

        for category, threats in categories.items():
            if threat in threats:
                description = descriptions.get(category, "")
                return (
                    f"{threat_name} pertenece a la categoria: {category.upper()}\n"
                    f"{description}"
                )

        return "No he podido clasificar la amenaza en una categoria."

    def confirm_deny_handler(self, text):
        data = dl.load("confirmar_negar")
        normalized = normalize_text(text)

        for option in data.get("confirmations", []):
            if normalize_text(option) in normalized:
                return random.choice(data.get("responses", {}).get("confirmed", []))

        for option in data.get("negations", []):
            if normalize_text(option) in normalized:
                return random.choice(data.get("responses", {}).get("denied", []))

        return (
            "No he entendido si confirmas o niegas el diagnostico. "
            "Puedes responder con 'si', 'no', 'correcto' o 'no es eso'."
        )

    def steps_to_follow_handler(self, text):
        steps_dataset = dl.load("solicitar_pasos")
        report_dataset = dl.load("reportar_problema")
        threat, _, _ = self.engine.evaluate(text, report_dataset)

        if not threat:
            threat = self.session.last_threat

        if not threat or threat not in steps_dataset.get("steps", {}):
            return (
                "Necesito saber que amenaza quieres resolver.\n"
                "Describe primero el problema y luego pideme los pasos."
            )

        threat_name = THREAT_NAMES.get(threat, threat)
        lines = [f"Pasos para responder a {threat_name}:"]

        for step in steps_dataset["steps"][threat]:
            lines.append(f"  {step}")

        return "\n".join(lines)

    def long_case_handler(self, text):
        data = dl.load("explicar_caso_largo")
        responses = data.get("responses", {})
        already_collecting = self.session.long_case

        self.session.update_facts(text)
        self.session.set_long_case(True)

        dataset = dl.load("reportar_problema")
        threat, score, all_scores = self.engine.evaluate(text, dataset)

        if threat is None and len(self.session.known_facts) > 1:
            accumulated = self.engine.forward_chaining(self.session.known_facts, dataset)
            if accumulated:
                threat, score = next(iter(accumulated.items()))
                all_scores = accumulated

        if threat:
            self.session.set_threat(threat)
            self.session.set_long_case(False)
            threat_data = dataset["threats"][threat]
            diagnosis = self.format_diagnosis(threat, threat_data, score, all_scores)
            ack_finish = responses.get(
                "ack_finish",
                "Gracias por los detalles. Ya puedo darte un diagnostico.",
            )
            return f"{ack_finish}\n\n{diagnosis}"

        if already_collecting:
            return random.choice(
                responses.get(
                    "ack_continue",
                    ["Entendido. Si puedes, dame un poco mas de detalle."],
                )
            )

        return random.choice(
            responses.get(
                "ack_start",
                ["Adelante, cuentame el caso con detalle."],
            )
        )

    def good_practices_handler(self, _text):
        data = dl.load("buenas_practicas")
        lines = ["Buenas practicas de ciberseguridad:"]

        for practice in data.get("practices", []):
            lines.append("")
            lines.append(f"- {practice.get('title', '')}")
            lines.append(f"  {practice.get('detail', '')}")

        return "\n".join(lines)

    def no_diagnosis(self):
        if self.session.turn_count > 2:
            return (
                "Todavia no puedo identificar la amenaza.\n"
                "Dame mas detalles: que ha dejado de funcionar, que mensajes ves "
                "en pantalla o cuando empezo el problema."
            )

        return (
            "No he detectado ninguna amenaza conocida.\n"
            "Prueba con sintomas concretos, por ejemplo:\n"
            "  - 'mis archivos tienen una extension rara y me piden bitcoin'\n"
            "  - 'he recibido un correo sospechoso del banco'\n"
            "  - 'veo muchos intentos fallidos de login'"
        )

    def format_diagnosis(self, threat, threat_data, score, all_scores):
        threat_name = THREAT_NAMES.get(threat, threat)
        severity = threat_data.get("severity", "desconocida")
        severity_labels = {
            "critica": "CRITICA",
            "alta": "ALTA",
            "media": "MEDIA",
            "baja": "BAJA",
        }
        severity_label = severity_labels.get(severity, severity.upper())

        lines = [
            f"Amenaza identificada: {threat_name}",
            f"Puntuacion: {score:.2f} | Severidad: {severity_label}",
            "",
            f"Descripcion: {threat_data.get('description', '')}",
        ]

        alternatives = []
        for candidate, candidate_score in list(all_scores.items())[1:3]:
            candidate_name = THREAT_NAMES.get(candidate, candidate)
            alternatives.append(f"{candidate_name} ({candidate_score:.2f})")

        if alternatives:
            lines.append(f"Otras posibles: {', '.join(alternatives)}")

        recommendations = threat_data.get("recommendations", [])
        if recommendations:
            lines.append("")
            lines.append("Recomendaciones:")
            for index, item in enumerate(recommendations, start=1):
                lines.append(f"  {index}. {item}")

        lines.append("")
        lines.append(
            "Si quieres, puedo darte pasos detallados, mas informacion o "
            "recomendaciones especificas."
        )
        return "\n".join(lines)

    def _fallback_intent(self, text):
        normalized = normalize_text(text)
        tokens = normalized.split()

        if self._is_short_confirmation_or_denial(normalized, tokens):
            return "confirmar_negar"

        if self._contains_any(normalized, ["pasos", "paso a paso", "que hago"]):
            return "solicitar_pasos"

        if self._contains_any(normalized, ["recomend", "protejo", "prevenir", "evitar"]):
            return "solicitar_recomendaciones"

        if self._contains_any(normalized, ["que es", "explicame", "informacion", "definicion"]):
            return "buscar_informacion"

        if self._contains_any(normalized, ["categoria", "tipo de ataque", "clasific"]):
            return "detectar_categoria"

        if self._contains_any(normalized, ["ayuda", "menu", "opciones", "que puedes hacer"]):
            return "pedir_ayuda"

        return "reportar_problema"

    def _contains_any(self, text, fragments):
        return any(fragment in text for fragment in fragments)

    def _is_short_confirmation_or_denial(self, normalized, tokens):
        if len(tokens) > 4:
            return False

        answers = {
            "si",
            "no",
            "correcto",
            "exacto",
            "vale",
            "claro",
            "no es eso",
            "no exactamente",
        }
        return normalized in answers

    def run(self):
        print("\n" + "=" * 55)
        print("       CYBERBOT - Sistema Experto en Ciberseguridad")
        print("=" * 55)
        print("Escribe 'ayuda' para ver las opciones.\n")

        while True:
            try:
                user_input = input("Tu: ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ["salir", "exit", "quit"]:
                    print(f"\nCyberBot: {self.farewell_handler(user_input)}\n")
                    break

                if user_input.lower() in ["reset", "reiniciar"]:
                    self.session.reset()
                    print("\nCyberBot: Sesion reiniciada.\n")
                    continue

                response = self.process_input(user_input)
                print(f"\nCyberBot: {response}\n")
            except KeyboardInterrupt:
                print("\n\nCyberBot: Hasta luego.\n")
                break
            except Exception as error:
                print(f"\nCyberBot: Error inesperado: {error}\n")
