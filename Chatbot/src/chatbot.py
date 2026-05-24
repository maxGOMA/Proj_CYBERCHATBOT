import random

import src.dataset_loader as dl
import src.inference_engine as ie
from src.nlp_utils import clean_text
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


class Chatbot:
    def __init__(self, intent_model):
        self.intent_model = intent_model
        self.session = Session()
        self.handlers = {
            "saludar": self.greet_handler,
            "despedirse": self.farewell_handler,
            "pedir_ayuda": self.help_handler,
            "reportar_problema": self.report_problem_handler,
            "solicitar_diagnostico": self.report_problem_handler,
            "buscar_informacion": self.information_handler,
            "solicitar_recomendaciones": self.recommendations_handler,
            "detectar_categoria": self.category_handler,
            "confirmar_negar": self.confirm_deny_handler,
            "solicitar_pasos": self.steps_handler,
            "explicar_caso_largo": self.long_case_handler,
            "buenas_practicas": self.good_practices_handler,
        }

    def process_input(self, user_text):
        self.session.add_message("user", user_text)

        intent_name, intent_score = ie.detect_intent(user_text, self.intent_model)
        if intent_score < ie.INTENT_THRESHOLD:
            intent_name = self.fallback_intent(user_text)

        self.session.set_intent(intent_name)

        if intent_name in self.handlers:
            response = self.handlers[intent_name](user_text)
        else:
            response = self.report_problem_handler(user_text)

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
        self.session.update_facts(text)

        threat_name, score, all_scores = ie.detect_threat(text, dataset)

        if threat_name is None and len(self.session.known_facts) > 1:
            threat_name, score, all_scores = ie.detect_threat_from_history(
                self.session.known_facts,
                dataset,
            )

        if threat_name is None:
            return self.no_diagnosis()

        self.session.set_threat(threat_name)
        threat_data = dataset["threats"][threat_name]
        return self.format_diagnosis(threat_name, threat_data, score, all_scores)

    def information_handler(self, text):
        dataset = dl.load("buscar_informacion")
        threat_name = ie.detect_info_threat(text, dataset)

        if threat_name is None:
            threat_name = self.session.last_threat

        if threat_name is None:
            return (
                "No he encontrado informacion sobre ese tema.\n"
                "Prueba con frases como: 'que es el phishing' o "
                "'explicame el ransomware'."
            )

        threat_data = dataset["threats"][threat_name]
        visible_name = THREAT_NAMES.get(threat_name, threat_name)

        lines = [visible_name]

        if "summary" in threat_data:
            lines.append("")
            lines.append("Resumen: " + threat_data["summary"])

        if "detail" in threat_data:
            lines.append("")
            lines.append("Detalle: " + threat_data["detail"])

        return "\n".join(lines)

    def recommendations_handler(self, text):
        recommendations = dl.load("solicitar_recomendaciones")
        report_dataset = dl.load("reportar_problema")
        threat_name, _, _ = ie.detect_threat(text, report_dataset)

        if threat_name is None:
            threat_name = self.session.last_threat

        if threat_name and threat_name in recommendations.get("by_threat", {}):
            lines = [f"Recomendaciones para {THREAT_NAMES.get(threat_name, threat_name)}:"]

            for index, item in enumerate(recommendations["by_threat"][threat_name], 1):
                lines.append(f"  {index}. {item}")

            return "\n".join(lines)

        lines = ["Buenas practicas generales:"]

        for index, item in enumerate(recommendations.get("general", []), 1):
            lines.append(f"  {index}. {item}")

        return "\n".join(lines)

    def category_handler(self, text):
        category_dataset = dl.load("detectar_categoria")
        report_dataset = dl.load("reportar_problema")
        threat_name, _, _ = ie.detect_threat(text, report_dataset)

        if threat_name is None:
            threat_name = self.session.last_threat

        if threat_name is None:
            return "No he detectado una amenaza concreta todavia."

        categories = category_dataset.get("categories", {})
        descriptions = category_dataset.get("category_descriptions", {})

        for category_name, threat_list in categories.items():
            if threat_name in threat_list:
                return (
                    f"{THREAT_NAMES.get(threat_name, threat_name)} pertenece a la categoria "
                    f"{category_name.upper()}.\n{descriptions.get(category_name, '')}"
                )

        return "No he podido clasificar la amenaza."

    def confirm_deny_handler(self, text):
        dataset = dl.load("confirmar_negar")
        answer_type = ie.classify_yes_no(clean_text(text), dataset)

        if answer_type == "yes":
            return random.choice(dataset.get("responses", {}).get("confirmed", []))

        if answer_type == "no":
            return random.choice(dataset.get("responses", {}).get("denied", []))

        return "No he entendido si confirmas o niegas el diagnostico."

    def steps_handler(self, text):
        steps_dataset = dl.load("solicitar_pasos")
        report_dataset = dl.load("reportar_problema")
        threat_name, _, _ = ie.detect_threat(text, report_dataset)

        if threat_name is None:
            threat_name = self.session.last_threat

        if threat_name is None or threat_name not in steps_dataset.get("steps", {}):
            return "Primero necesito saber que amenaza quieres resolver."

        lines = [f"Pasos para responder a {THREAT_NAMES.get(threat_name, threat_name)}:"]

        for step in steps_dataset["steps"][threat_name]:
            lines.append(f"  {step}")

        return "\n".join(lines)

    def long_case_handler(self, text):
        data = dl.load("explicar_caso_largo")
        self.session.update_facts(text)

        threat_name, score, all_scores = ie.detect_threat_from_history(
            self.session.known_facts,
            dl.load("reportar_problema"),
        )

        if threat_name is None:
            if self.session.long_case:
                return random.choice(
                    data.get("responses", {}).get(
                        "ack_continue",
                        ["Continua, dame mas detalles del caso."],
                    )
                )

            self.session.set_long_case(True)
            return random.choice(
                data.get("responses", {}).get(
                    "ack_start",
                    ["Adelante, cuentame el caso con detalle."],
                )
            )

        self.session.set_threat(threat_name)
        self.session.set_long_case(False)

        threat_data = dl.load("reportar_problema")["threats"][threat_name]
        diagnosis = self.format_diagnosis(threat_name, threat_data, score, all_scores)
        finish_text = data.get("responses", {}).get(
            "ack_finish",
            "Gracias por los detalles.",
        )
        return finish_text + "\n\n" + diagnosis

    def good_practices_handler(self, _text):
        data = dl.load("buenas_practicas")
        lines = ["Buenas practicas de ciberseguridad:"]

        for practice in data.get("practices", []):
            lines.append("")
            lines.append("- " + practice.get("title", ""))
            lines.append("  " + practice.get("detail", ""))

        return "\n".join(lines)

    def no_diagnosis(self):
        if self.session.turn_count > 2:
            return (
                "No he podido identificar la amenaza con claridad.\n"
                "Dame mas detalles sobre sintomas, mensajes en pantalla o cuando empezo."
            )

        return (
            "No he detectado una amenaza conocida.\n"
            "Prueba con frases como:\n"
            "  - 'mis archivos estan cifrados'\n"
            "  - 'he recibido un correo sospechoso'\n"
            "  - 'hay muchos intentos fallidos de login'"
        )

    def format_diagnosis(self, threat_name, threat_data, score, all_scores):
        visible_name = THREAT_NAMES.get(threat_name, threat_name)
        lines = [
            "Amenaza identificada: " + visible_name,
            f"Puntuacion: {score}",
            "Descripcion: " + threat_data.get("description", ""),
        ]

        if len(all_scores) > 1:
            alternatives = []

            for other_name, other_score in list(all_scores.items())[1:3]:
                label = THREAT_NAMES.get(other_name, other_name)
                alternatives.append(f"{label} ({other_score})")

            lines.append("Otras posibles: " + ", ".join(alternatives))

        if threat_data.get("recommendations"):
            lines.append("")
            lines.append("Recomendaciones:")

            for index, item in enumerate(threat_data["recommendations"], 1):
                lines.append(f"  {index}. {item}")

        return "\n".join(lines)

    def fallback_intent(self, text):
        clean = clean_text(text)

        if "hola" in clean or "buenas" in clean or "saludos" in clean:
            return "saludar"

        if "adios" in clean or "hasta luego" in clean or "chao" in clean:
            return "despedirse"

        if clean in ["si", "no", "vale", "correcto", "exacto"]:
            return "confirmar_negar"

        if "buenas practicas" in clean or "consejos generales" in clean:
            return "buenas_practicas"

        if "paso" in clean or "pasos" in clean:
            return "solicitar_pasos"

        if "recomend" in clean or "proteg" in clean or "evitar" in clean:
            return "solicitar_recomendaciones"

        if "que es" in clean or "explicame" in clean or "informacion" in clean:
            return "buscar_informacion"

        if "categoria" in clean or "tipo de ataque" in clean:
            return "detectar_categoria"

        if "ayuda" in clean or "menu" in clean or "opciones" in clean:
            return "pedir_ayuda"

        return "reportar_problema"

    def run(self):
        print("\n" + "=" * 55)
        print("       CYBERBOT - Sistema Experto en Ciberseguridad")
        print("=" * 55)
        print("Escribe 'ayuda' para ver las opciones.\n")

        while True:
            try:
                user_text = input("Tu: ").strip()

                if not user_text:
                    continue

                if user_text.lower() in ["salir", "exit", "quit"]:
                    print("\nCyberBot: " + self.farewell_handler(user_text) + "\n")
                    break

                if user_text.lower() in ["reset", "reiniciar"]:
                    self.session.reset()
                    print("\nCyberBot: Sesion reiniciada.\n")
                    continue

                response = self.process_input(user_text)
                print("\nCyberBot: " + response + "\n")
            except KeyboardInterrupt:
                print("\n\nCyberBot: Hasta luego.\n")
                break
            except Exception as error:
                print("\nCyberBot: Error inesperado: " + str(error) + "\n")
