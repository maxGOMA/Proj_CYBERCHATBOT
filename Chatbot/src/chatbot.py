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

CATEGORY_NAMES = {
    "malware": "Malware",
    "ingenieria_social": "Ingenieria social",
    "ataque_red": "Ataque de red",
    "ataque_aplicacion": "Ataque a aplicacion",
    "acceso_no_autorizado": "Acceso no autorizado",
    "amenaza_interna": "Amenaza interna",
}

CLARIFYING_QUESTIONS = {
    "phishing": (
        "Dime si has visto un correo, SMS o pagina falsa pidiendote credenciales."
    ),
    "ransomware": (
        "Confirma si tus archivos aparecen cifrados, con extension cambiada o con una nota de rescate."
    ),
    "ddos": (
        "Necesito saber si el problema es un servicio web/servidor saturado o si tu PC individual va lento."
    ),
    "sql_injection": (
        "Indica si ves errores SQL, formularios vulnerables o acceso extrano a la base de datos."
    ),
    "malware": (
        "Cuentame si ves procesos desconocidos, uso alto de CPU, ventiladores disparados, popups o programas raros."
    ),
    "man_in_the_middle": (
        "Aclara si estabas en una WiFi publica o si el navegador mostro avisos de certificado invalido."
    ),
    "brute_force": (
        "Dime si hay multiples intentos fallidos de acceso, bloqueos de cuenta o logs repetidos de login."
    ),
    "insider_threat": (
        "Necesito saber si hubo acceso interno indebido, copia de datos o actividad fuera de horario."
    ),
}


class Chatbot:
    def __init__(self, intent_model, threat_model=None, info_model=None):
        self.intent_model = intent_model
        self.session = Session()
        self.datasets = dl.load_all()
        self.report_dataset = self.datasets["reportar_problema"]
        self.info_dataset = self.datasets["buscar_informacion"]
        self.recommendations_dataset = self.datasets["solicitar_recomendaciones"]
        self.steps_dataset = self.datasets["solicitar_pasos"]
        self.category_dataset = self.datasets["detectar_categoria"]
        self.threat_model = threat_model or ie.build_threat_model(self.report_dataset)
        self.info_model = info_model or ie.build_info_model(self.info_dataset)
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

    def get_welcome_message(self):
        return (
            "Soy CyberBot. Describe lo que te esta pasando y te ayudare a "
            "estimar la amenaza, entenderla y decidir los siguientes pasos.\n\n"
            "Prueba con mensajes como:\n"
            "- 'mi PC va muy lento y la CPU esta al 100%'\n"
            "- 'he recibido un correo del banco pidiendome la contrasena'\n"
            "- 'mis archivos no abren y me piden un rescate'\n"
            "- 'buenas practicas'\n"
            "- 'amenazas'"
        )

    def get_quick_prompts(self):
        return [
            "Mi PC va lento y hay un proceso raro",
            "He recibido un correo sospechoso del banco",
            "Mis archivos se han cifrado",
            "Como me protejo del phishing",
            "Pasos para resolver malware",
        ]

    def get_status(self):
        context = self.session.get_context()
        threat = context["last_threat"]
        confidence = context["last_confidence"]
        return {
            "threat": THREAT_NAMES.get(threat, "Sin diagnostico") if threat else "Sin diagnostico",
            "confidence": f"{int(confidence * 100)}%" if confidence else "-",
            "turns": context["turn_count"],
            "facts": len(context["known_facts"]),
        }

    def reset_session(self):
        self.session.reset()
        return "Sesion reiniciada. Puedes contarme el problema desde cero."

    def process_input(self, user_text):
        text = (user_text or "").strip()
        if not text:
            return "Escribe una descripcion del problema o una pregunta concreta."

        self.session.add_message("user", text)
        normalized = clean_text(text)
        command_response = self.handle_command(normalized)

        if command_response is not None:
            self.session.add_message("bot", command_response)
            return command_response

        intent_name, intent_score = ie.detect_intent(text, self.intent_model)
        if intent_score < ie.INTENT_THRESHOLD:
            intent_name = self.fallback_intent(text)

        self.session.set_intent(intent_name)
        handler = self.handlers.get(intent_name, self.report_problem_handler)
        response = handler(text)
        self.session.add_message("bot", response)
        return response

    def handle_command(self, normalized_text):
        if normalized_text in {"reset", "reiniciar", "reiniciar sesion"}:
            return self.reset_session()

        if normalized_text in {
            "amenazas",
            "lista de amenazas",
            "lista amenazas",
            "que amenazas conoces",
        }:
            return self.list_threats_handler()

        if normalized_text in {"estado", "resumen", "contexto"}:
            return self.status_handler()

        return None

    def greet_handler(self, _text):
        data = self.datasets["saludar"]
        responses = data.get("responses", ["Hola. En que puedo ayudarte?"])
        return random.choice(responses)

    def farewell_handler(self, _text):
        data = self.datasets["despedirse"]
        responses = data.get("responses", ["Hasta luego."])
        return random.choice(responses)

    def help_handler(self, _text):
        data = self.datasets["pedir_ayuda"]
        response = data.get("response", {})
        lines = [response.get("intro", "Puedo ayudarte con lo siguiente:")]

        for option in response.get("options", []):
            lines.append(f"- {option}")

        lines.extend(
            [
                "",
                "Comandos utiles:",
                "- 'reset' para reiniciar la sesion",
                "- 'amenazas' para ver las amenazas conocidas",
                "- 'estado' para ver el contexto actual",
            ]
        )
        return "\n".join(lines)

    def report_problem_handler(self, text):
        self.session.update_facts(text)

        threat_name, score, all_scores, evidence = ie.detect_threat(
            text,
            self.report_dataset,
            self.threat_model,
        )

        if threat_name is None and len(self.session.known_facts) > 1:
            threat_name, score, all_scores, evidence = ie.detect_threat_from_history(
                self.session.known_facts,
                self.report_dataset,
                self.threat_model,
            )

        if threat_name is None:
            return self.no_diagnosis(all_scores, evidence)

        threat_data = self.report_dataset["threats"][threat_name]
        matched_terms = evidence.get(threat_name, {}).get("matched_terms", [])
        self.session.set_threat(threat_name, confidence=score, evidence=matched_terms)
        return self.format_diagnosis(
            threat_name,
            threat_data,
            score,
            all_scores,
            evidence,
            source_text=text,
        )

    def information_handler(self, text):
        threat_name = ie.detect_info_threat(text, self.info_dataset, self.info_model)

        if threat_name is None:
            threat_name = self.session.last_threat

        if threat_name is None:
            return (
                "No he encontrado informacion suficientemente clara sobre ese tema.\n"
                "Prueba con frases como 'que es el phishing' o 'explicame el ransomware'."
            )

        threat_data = self.info_dataset["threats"][threat_name]
        visible_name = threat_data.get("title", THREAT_NAMES.get(threat_name, threat_name))
        lines = [visible_name]

        if threat_data.get("summary"):
            lines.extend(["", "Resumen: " + threat_data["summary"]])

        if threat_data.get("detail"):
            lines.extend(["", "Detalle: " + threat_data["detail"]])

        lines.extend(
            [
                "",
                "Si quieres, luego puedes pedirme 'pasos para resolverlo' o 'como me protejo'.",
            ]
        )
        return "\n".join(lines)

    def recommendations_handler(self, text):
        normalized_text = clean_text(text)

        if "general" in normalized_text or "buenas practicas" in normalized_text:
            threat_name = None
        else:
            threat_name, _, _, _ = ie.detect_threat(
                text,
                self.report_dataset,
                self.threat_model,
            )

        if threat_name is None:
            threat_name = self.session.last_threat

        if threat_name and threat_name in self.recommendations_dataset.get("by_threat", {}):
            lines = [
                f"Recomendaciones para {THREAT_NAMES.get(threat_name, threat_name)}:"
            ]

            for index, item in enumerate(
                self.recommendations_dataset["by_threat"][threat_name],
                1,
            ):
                lines.append(f"{index}. {item}")

            return "\n".join(lines)

        lines = ["Buenas practicas generales:"]

        for index, item in enumerate(self.recommendations_dataset.get("general", []), 1):
            lines.append(f"{index}. {item}")

        return "\n".join(lines)

    def category_handler(self, text):
        threat_name, _, _, _ = ie.detect_threat(text, self.report_dataset, self.threat_model)

        if threat_name is None:
            threat_name = self.session.last_threat

        if threat_name is None:
            return "No he detectado una amenaza concreta todavia."

        categories = self.category_dataset.get("categories", {})

        for category_name, category_data in categories.items():
            if threat_name in category_data.get("subcategories", []):
                readable_category = CATEGORY_NAMES.get(category_name, category_name)
                return (
                    f"{THREAT_NAMES.get(threat_name, threat_name)} encaja en la categoria "
                    f"{readable_category}.\n{category_data.get('description', '')}"
                )

        return "No he podido clasificar la amenaza."

    def confirm_deny_handler(self, text):
        dataset = self.datasets["confirmar_negar"]
        answer_type = ie.classify_yes_no(text, dataset)

        if answer_type == "yes":
            options = dataset.get("responses", {}).get(
                "confirm",
                ["Entendido. Seguimos con ese diagnostico."],
            )
            response = random.choice(options)
            if self.session.last_threat:
                response += " Puedes pedirme pasos concretos o recomendaciones."
            return response

        if answer_type == "no":
            options = dataset.get("responses", {}).get(
                "deny",
                ["De acuerdo. Dame mas detalles para revisar otra posibilidad."],
            )
            response = random.choice(options)
            return response

        return "No he entendido si confirmas o niegas el diagnostico."

    def steps_handler(self, text):
        threat_name, _, _, _ = ie.detect_threat(text, self.report_dataset, self.threat_model)

        if threat_name is None:
            threat_name = self.session.last_threat

        if threat_name is None or threat_name not in self.steps_dataset.get("steps", {}):
            return (
                "Primero necesito saber que amenaza quieres resolver. "
                "Describe el problema o dime el nombre de la amenaza."
            )

        lines = [f"Pasos para responder a {THREAT_NAMES.get(threat_name, threat_name)}:"]

        for step in self.steps_dataset["steps"][threat_name]:
            lines.append(step)

        return "\n".join(lines)

    def long_case_handler(self, text):
        data = self.datasets["explicar_caso_largo"]
        self.session.update_facts(text)

        threat_name, score, all_scores, evidence = ie.detect_threat_from_history(
            self.session.known_facts,
            self.report_dataset,
            self.threat_model,
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

        self.session.set_long_case(False)
        threat_data = self.report_dataset["threats"][threat_name]
        matched_terms = evidence.get(threat_name, {}).get("matched_terms", [])
        self.session.set_threat(threat_name, confidence=score, evidence=matched_terms)
        diagnosis = self.format_diagnosis(
            threat_name,
            threat_data,
            score,
            all_scores,
            evidence,
            source_text=" ".join(self.session.known_facts),
        )
        finish_text = data.get("responses", {}).get(
            "ack_finish",
            "Gracias por los detalles.",
        )
        return finish_text + "\n\n" + diagnosis

    def good_practices_handler(self, _text):
        data = self.datasets["buenas_practicas"]
        lines = ["Buenas practicas de ciberseguridad:"]

        for practice in data.get("practices", []):
            lines.append("")
            lines.append("- " + practice.get("title", ""))
            lines.append("  " + practice.get("detail", ""))

        return "\n".join(lines)

    def list_threats_handler(self):
        threat_names = [
            THREAT_NAMES.get(threat_name, threat_name)
            for threat_name in self.report_dataset.get("threats", {})
        ]
        lines = ["Amenazas conocidas por este asistente:"]
        lines.extend(f"- {name}" for name in threat_names)
        lines.extend(
            [
                "",
                "Tambien puedes describir sintomas sin saber el nombre tecnico.",
            ]
        )
        return "\n".join(lines)

    def status_handler(self):
        status = self.get_status()
        evidence = ", ".join(self.session.last_evidence) if self.session.last_evidence else "sin evidencias guardadas"
        return (
            f"Amenaza actual: {status['threat']}\n"
            f"Confianza: {status['confidence']}\n"
            f"Turnos: {status['turns']}\n"
            f"Hechos recordados: {status['facts']}\n"
            f"Evidencias: {evidence}"
        )

    def no_diagnosis(self, all_scores=None, evidence=None):
        lines = [
            "No tengo un diagnostico suficientemente fiable todavia.",
        ]

        if all_scores:
            top_candidates = list(all_scores.items())[:2]
            pretty_candidates = ", ".join(
                f"{THREAT_NAMES.get(name, name)} ({int(score * 100)}%)"
                for name, score in top_candidates
                if score >= 0.10
            )

            if pretty_candidates:
                lines.append("Lo mas cercano ahora mismo es: " + pretty_candidates)
                lines.append("")
                lines.append(self.build_clarifying_question(top_candidates[0][0]))
                return "\n".join(lines)

        if self.session.turn_count > 2:
            lines.append(
                "Dame mas detalles sobre sintomas, mensajes en pantalla, uso anormal de recursos o cuando empezo."
            )
            return "\n".join(lines)

        lines.extend(
            [
                "Prueba con frases como:",
                "- 'mi PC va lento y hay un proceso desconocido'",
                "- 'he recibido un correo sospechoso'",
                "- 'hay muchos intentos fallidos de login'",
                "- 'mis archivos aparecen cifrados'",
            ]
        )
        return "\n".join(lines)

    def build_clarifying_question(self, threat_name):
        return CLARIFYING_QUESTIONS.get(
            threat_name,
            "Necesito alguna pista mas para afinar el diagnostico.",
        )

    def confidence_label(self, score):
        if score >= 0.72:
            return "alta"
        if score >= 0.45:
            return "media"
        return "baja"

    def format_alternatives(self, threat_name, all_scores):
        alternatives = []

        for other_name, other_score in list(all_scores.items())[1:3]:
            if other_name == threat_name or other_score < 0.12:
                continue

            label = THREAT_NAMES.get(other_name, other_name)
            alternatives.append(f"{label} ({int(other_score * 100)}%)")

        return alternatives

    def looks_like_cryptominer(self, source_text, matched_terms):
        normalized_text = clean_text(source_text)
        mining_signals = {
            "cpu",
            "procesador",
            "ventilador",
            "criptomoneda",
            "mineria",
            "troyano",
            "lento",
            "se calienta",
        }

        if any(signal in normalized_text for signal in mining_signals):
            return True

        return any("criptomoneda" in term or "troyano" in term for term in matched_terms)

    def format_diagnosis(self, threat_name, threat_data, score, all_scores, evidence, source_text=""):
        visible_name = THREAT_NAMES.get(threat_name, threat_name)
        matched_terms = evidence.get(threat_name, {}).get("matched_terms", [])
        lines = [
            f"Diagnostico probable: {visible_name}",
            f"Confianza estimada: {int(score * 100)}% ({self.confidence_label(score)})",
            f"Riesgo: {str(threat_data.get('severity', 'media')).upper()}",
            "",
            "Por que lo sospecho:",
        ]

        if matched_terms:
            lines.append("- Sintomas detectados: " + ", ".join(matched_terms))
        else:
            lines.append("- Coincide con el patron general de la amenaza.")

        lines.append("- Descripcion: " + threat_data.get("description", ""))

        if threat_name == "malware" and self.looks_like_cryptominer(source_text, matched_terms):
            lines.append(
                "- Ademas, los sintomas recuerdan a un posible troyano minero o malware que consume recursos."
            )

        alternatives = self.format_alternatives(threat_name, all_scores)
        if alternatives:
            lines.extend(["", "Otras posibilidades:", "- " + " | ".join(alternatives)])

        recommendations = threat_data.get("recommendations", [])
        if recommendations:
            lines.extend(["", "Que haria ahora:"])
            for index, item in enumerate(recommendations[:4], 1):
                lines.append(f"{index}. {item}")

        if threat_name == "malware" and self.looks_like_cryptominer(source_text, matched_terms):
            lines.append(
                "5. Si el consumo anormal persiste tras limpiar el sistema, valora reinstalar o resetear el equipo."
            )

        lines.extend(
            [
                "",
                "Puedes seguir con:",
                "- 'pasos para resolverlo'",
                "- 'como me protejo'",
                "- 'que es esta amenaza'",
            ]
        )
        return "\n".join(lines)

    def fallback_intent(self, text):
        clean = clean_text(text)

        if "hola" in clean or "buenas" in clean or "saludos" in clean:
            return "saludar"

        if "adios" in clean or "hasta luego" in clean or "chao" in clean:
            return "despedirse"

        if clean in {"si", "no", "vale", "correcto", "exacto", "ok"}:
            return "confirmar_negar"

        if "buenas practicas" in clean or "consejos generales" in clean:
            return "buenas_practicas"

        if "paso" in clean or "pasos" in clean or "guia" in clean:
            return "solicitar_pasos"

        if "recomend" in clean or "proteg" in clean or "evitar" in clean or "prevenir" in clean:
            return "solicitar_recomendaciones"

        if "que es" in clean or "explicame" in clean or "informacion" in clean or "definicion" in clean:
            return "buscar_informacion"

        if "categoria" in clean or "tipo de ataque" in clean or "que tipo es" in clean:
            return "detectar_categoria"

        if "ayuda" in clean or "menu" in clean or "opciones" in clean:
            return "pedir_ayuda"

        if len(clean.split()) >= 12:
            return "explicar_caso_largo"

        return "reportar_problema"

    def run(self):
        print("\n" + "=" * 62)
        print("                    CYBERBOT")
        print("         Asistente conversacional de ciberseguridad")
        print("=" * 62)
        print(self.get_welcome_message() + "\n")
        print("Escribe 'ayuda' para ver opciones, 'reset' para reiniciar o 'salir' para terminar.\n")

        while True:
            try:
                user_text = input("Tu: ").strip()

                if not user_text:
                    continue

                if clean_text(user_text) in {"salir", "exit", "quit"}:
                    print("\nCyberBot: " + self.farewell_handler(user_text) + "\n")
                    break

                response = self.process_input(user_text)
                print("\nCyberBot: " + response + "\n")
            except KeyboardInterrupt:
                print("\n\nCyberBot: Hasta luego.\n")
                break
            except Exception as error:
                print("\nCyberBot: Error inesperado: " + str(error) + "\n")
