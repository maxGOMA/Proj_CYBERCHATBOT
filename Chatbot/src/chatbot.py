import random

import src.dataset_loader as dl
import src.inference_engine as ie
from src.nlp_utils import clean_text
from src.nlp_utils import text_contains_term
from src.session import Session

THREAT_NAMES = {
    "phishing": "Phishing",
    "ransomware": "Ransomware",
    "ddos": "Ataque DDoS",
    "sql_injection": "Inyeccion SQL",
    "malware": "Malware / Virus",
    "man_in_the_middle": "Man-in-the-Middle",
    "brute_force": "Fuerza Bruta",
    "insider_threat": "Amenaza Interna"
}

CATEGORY_NAMES = {
    "red": "Ataque de red",
    "credenciales": "Robo o ataque de credenciales",
    "malware": "Malware",
    "aplicacion_web": "Ataque a aplicacion web",
    "interno": "Amenaza interna"
}


class Chatbot:
    def __init__(self):
        self.session = Session()
        self.datasets = dl.load_all()
        self.mobile_models_data = dl.load_mobile_models()
        self.intent_model = ie.build_intent_model(dl.build_examples_by_intent())
        self.threat_model = ie.build_threat_model(self.datasets["reportar_problema"])
        self.info_model = ie.build_info_model(self.datasets["buscar_informacion"])

    def get_welcome_message(self):
        return (
            "Hola, soy CyberBot.\n"
            "Puedo ayudarte a detectar amenazas de ciberseguridad y darte informacion basica.\n\n"
            "Ejemplos:\n"
            "- me han hackeado\n"
            "- he recibido un correo raro\n"
            "- mis archivos estan cifrados\n"
            "- que es el phishing\n"
            "- buenas practicas"
        )

    def get_status(self):
        context = self.session.get_context()
        threat_name = context["last_threat"]
        visible_threat = "Sin diagnostico"

        if threat_name is not None:
            visible_threat = THREAT_NAMES.get(threat_name, threat_name)

        return {
            "threat": visible_threat,
            "confidence": str(int(context["last_confidence"] * 100)) + "%",
            "turns": str(context["turn_count"]),
            "facts": str(len(context["known_facts"]))
        }

    def reset_session(self):
        self.session.reset()
        return "Sesion reiniciada."

    def process_input(self, user_text):
        text = user_text.strip()

        if text == "":
            return "Escribe algun mensaje."

        self.session.add_message("user", text)

        command_response = self.handle_command(text)
        if command_response is not None:
            self.session.add_message("bot", command_response)
            return command_response

        if self.should_use_mobile_brand_response(text):
            response = self.mobile_brand_handler(text)
            self.session.add_message("bot", response)
            return response

        intent_name, intent_score = ie.detect_intent(text, self.intent_model)

        if intent_name is None:
            intent_name = self.fallback_intent(text)

        self.session.set_intent(intent_name)

        if intent_name == "saludar":
            response = self.greet_handler()
        elif intent_name == "despedirse":
            response = self.farewell_handler()
        elif intent_name == "pedir_ayuda":
            response = self.help_handler()
        elif intent_name == "buscar_informacion":
            response = self.information_handler(text)
        elif intent_name == "solicitar_recomendaciones":
            response = self.recommendations_handler(text)
        elif intent_name == "detectar_categoria":
            response = self.category_handler(text)
        elif intent_name == "confirmar_negar":
            response = self.confirm_deny_handler(text)
        elif intent_name == "solicitar_pasos":
            response = self.steps_handler(text)
        elif intent_name == "buenas_practicas":
            response = self.good_practices_handler()
        elif intent_name == "explicar_caso_largo":
            response = self.long_case_handler(text)
        elif intent_name == "solicitar_diagnostico":
            response = self.diagnosis_handler(text)
        else:
            response = self.report_problem_handler(text)

        self.session.add_message("bot", response)
        return response

    def handle_command(self, text):
        normalized = clean_text(text)

        if normalized == "reset" or normalized == "reiniciar" or normalized == "reiniciar sesion":
            return self.reset_session()

        if normalized == "amenazas" or normalized == "lista de amenazas" or normalized == "lista amenazas":
            return self.list_threats_handler()

        if normalized == "estado" or normalized == "resumen" or normalized == "contexto":
            return self.status_handler()

        return None

    def greet_handler(self):
        responses = self.datasets["saludar"].get("responses", ["Hola"])
        return random.choice(responses)

    def farewell_handler(self):
        responses = self.datasets["despedirse"].get("responses", ["Hasta luego"])
        return random.choice(responses)

    def help_handler(self):
        data = self.datasets["pedir_ayuda"].get("response", {})
        text = data.get("intro", "Puedo ayudarte con esto:")
        options = data.get("options", [])

        for option in options:
            text = text + "\n- " + option

        return text

    def report_problem_handler(self, text):
        self.session.update_facts(text)
        threat_name, score, all_scores, evidence = ie.detect_threat(text, self.datasets["reportar_problema"], self.threat_model)

        if threat_name is None:
            if len(self.session.known_facts) > 1:
                threat_name, score, all_scores, evidence = ie.detect_threat_from_history(
                    self.session.known_facts,
                    self.datasets["reportar_problema"],
                    self.threat_model
                )

        if threat_name is None:
            return self.no_diagnosis()

        threat_data = self.datasets["reportar_problema"]["threats"][threat_name]
        matched_terms = evidence.get(threat_name, {}).get("matched_terms", [])
        self.session.set_threat(threat_name, score, matched_terms)

        return self.format_diagnosis(threat_name, threat_data, score, matched_terms)

    def information_handler(self, text):
        threat_name = ie.detect_info_threat(text, self.datasets["buscar_informacion"], self.info_model)

        if threat_name is None:
            threat_name = self.session.last_threat

        if threat_name is None:
            return "No he encontrado informacion clara sobre eso."

        threat_data = self.datasets["buscar_informacion"]["threats"][threat_name]
        answer = threat_data.get("title", threat_name)

        summary = threat_data.get("summary", "")
        detail = threat_data.get("detail", "")

        if summary != "":
            answer = answer + "\n\nResumen: " + summary

        if detail != "":
            answer = answer + "\n\nDetalle: " + detail

        return answer

    def recommendations_handler(self, text):
        normalized = clean_text(text)
        threat_name = None

        if "general" in normalized or "buenas practicas" in normalized:
            threat_name = None
        else:
            threat_name, score, all_scores, evidence = ie.detect_threat(
                text,
                self.datasets["reportar_problema"],
                self.threat_model
            )

        if threat_name is None:
            threat_name = self.session.last_threat

        recommendations_data = self.datasets["solicitar_recomendaciones"]

        if threat_name is not None:
            by_threat = recommendations_data.get("by_threat", {})
            if threat_name in by_threat:
                text = "Recomendaciones para " + THREAT_NAMES.get(threat_name, threat_name) + ":"
                items = by_threat[threat_name]
                number = 1

                for item in items:
                    text = text + "\n" + str(number) + ". " + item
                    number = number + 1

                return text

        text = "Recomendaciones generales:"
        general_items = recommendations_data.get("general", [])
        number = 1

        for item in general_items:
            text = text + "\n" + str(number) + ". " + item
            number = number + 1

        return text

    def category_handler(self, text):
        threat_name, score, all_scores, evidence = ie.detect_threat(
            text,
            self.datasets["reportar_problema"],
            self.threat_model
        )

        if threat_name is None:
            threat_name = self.session.last_threat

        if threat_name is None:
            return "Todavia no puedo decir la categoria."

        data = self.datasets["detectar_categoria"]
        categories = data.get("categories", {})
        descriptions = data.get("category_descriptions", {})

        for category_name in categories:
            threat_list = categories[category_name]

            if threat_name in threat_list:
                visible_name = CATEGORY_NAMES.get(category_name, category_name)
                description = descriptions.get(category_name, "")
                return "La categoria es: " + visible_name + "\n" + description

        return "No he podido clasificar la amenaza."

    def confirm_deny_handler(self, text):
        answer = ie.classify_yes_no(text, self.datasets["confirmar_negar"])

        if answer == "yes":
            options = self.datasets["confirmar_negar"].get("responses", {}).get("confirm", ["De acuerdo"])
            return random.choice(options)

        if answer == "no":
            options = self.datasets["confirmar_negar"].get("responses", {}).get("deny", ["Vale"])
            return random.choice(options)

        return "No he entendido si confirmas o niegas."

    def steps_handler(self, text):
        threat_name, score, all_scores, evidence = ie.detect_threat(
            text,
            self.datasets["reportar_problema"],
            self.threat_model
        )

        if threat_name is None:
            threat_name = self.session.last_threat

        steps_data = self.datasets["solicitar_pasos"].get("steps", {})

        if threat_name is None:
            return "Primero necesito saber de que amenaza hablamos."

        if threat_name not in steps_data:
            return "No tengo pasos concretos para esa amenaza."

        answer = "Pasos para " + THREAT_NAMES.get(threat_name, threat_name) + ":"
        steps = steps_data[threat_name]

        for step in steps:
            answer = answer + "\n" + step

        return answer

    def long_case_handler(self, text):
        self.session.set_long_case(True)
        self.session.update_facts(text)

        if len(self.session.known_facts) < 2:
            responses = self.datasets["explicar_caso_largo"].get("responses", {}).get("ack_continue", [])
            if len(responses) > 0:
                return random.choice(responses)
            else:
                return "Sigue contandome mas detalles."

        threat_name, score, all_scores, evidence = ie.detect_threat_from_history(
            self.session.known_facts,
            self.datasets["reportar_problema"],
            self.threat_model
        )

        if threat_name is None:
            return "Todavia no tengo suficiente informacion."

        threat_data = self.datasets["reportar_problema"]["threats"][threat_name]
        matched_terms = evidence.get(threat_name, {}).get("matched_terms", [])
        self.session.set_threat(threat_name, score, matched_terms)
        return self.format_diagnosis(threat_name, threat_data, score, matched_terms)

    def good_practices_handler(self):
        data = self.datasets["buenas_practicas"]
        practices = data.get("practices", [])
        text = "Buenas practicas de ciberseguridad:"

        for practice in practices:
            title = practice.get("title", "")
            detail = practice.get("detail", "")
            text = text + "\n\n- " + title + "\n" + detail

        return text

    def list_threats_handler(self):
        threats = self.datasets["reportar_problema"].get("threats", {})
        text = "Amenazas conocidas:"

        for threat_name in threats:
            visible_name = THREAT_NAMES.get(threat_name, threat_name)
            text = text + "\n- " + visible_name

        return text

    def status_handler(self):
        status = self.get_status()
        text = "Amenaza actual: " + status["threat"]
        text = text + "\nConfianza: " + status["confidence"]
        text = text + "\nTurnos: " + status["turns"]
        text = text + "\nHechos: " + status["facts"]

        if len(self.session.last_evidence) > 0:
            text = text + "\nEvidencias: " + ", ".join(self.session.last_evidence)

        return text

    def diagnosis_handler(self, text):
        self.session.update_facts(text)

        threat_name, score, all_scores, evidence = ie.detect_threat(
            text,
            self.datasets["reportar_problema"],
            self.threat_model
        )

        if threat_name is None:
            if len(self.session.known_facts) > 1:
                threat_name, score, all_scores, evidence = ie.detect_threat_from_history(
                    self.session.known_facts,
                    self.datasets["reportar_problema"],
                    self.threat_model
                )

        data = self.datasets["solicitar_diagnostico"]
        templates = data.get("response_template", {})

        if threat_name is None:
            return templates.get(
                "threat_not_found",
                "No he podido determinar la amenaza con la información proporcionada."
            )

        threat_data = self.datasets["reportar_problema"]["threats"][threat_name]
        matched_terms = evidence.get(threat_name, {}).get("matched_terms", [])
        self.session.set_threat(threat_name, score, matched_terms)

        visible_name = THREAT_NAMES.get(threat_name, threat_name)
        severity = str(threat_data.get("severity", "media")).upper()
        confidence = int(score * 100)
        description = threat_data.get("description", "")

        threats_list = self.build_threats_list(all_scores)

        if len(all_scores) > 1:
            template = templates.get("multiple_threats", "")
            if template != "":
                intro = template.replace("{threats_list}", threats_list)
                final_part = templates.get("threat_found", "")
                final_part = final_part.replace("{threat_name}", visible_name)
                final_part = final_part.replace("{severity}", severity)
                final_part = final_part.replace("{confidence}", str(confidence))
                final_part = final_part.replace("{description}", description)
                return intro + "\n\n" + final_part

        template = templates.get("threat_found", "")
        template = template.replace("{threat_name}", visible_name)
        template = template.replace("{severity}", severity)
        template = template.replace("{confidence}", str(confidence))
        template = template.replace("{description}", description)

        return template

    def mobile_brand_handler(self, _text):
        return (
            "La marca o el modelo del móvil no es información suficiente para resolver el problema.\n"
            "Indica claramente qué problema tiene en específico."
        )

    def no_diagnosis(self):
        return (
            "No tengo un diagnostico claro todavia.\n"
            "Prueba a describir mejor los sintomas.\n"
            "Ejemplos:\n"
            "- he recibido un correo sospechoso\n"
            "- mis archivos estan cifrados\n"
            "- hay muchos intentos de acceso"
        )

    def format_diagnosis(self, threat_name, threat_data, score, matched_terms):
        visible_name = THREAT_NAMES.get(threat_name, threat_name)
        text = "Diagnostico probable: " + visible_name
        text = text + "\nConfianza estimada: " + str(int(score * 100)) + "%"
        text = text + "\nRiesgo: " + str(threat_data.get("severity", "media")).upper()

        description = threat_data.get("description", "")
        if description != "":
            text = text + "\n\nDescripcion: " + description

        if len(matched_terms) > 0:
            text = text + "\n\nSintomas detectados: " + ", ".join(matched_terms)

        recommendations = threat_data.get("recommendations", [])
        if len(recommendations) > 0:
            text = text + "\n\nQue puedes hacer ahora:"
            count = 1
            for item in recommendations[:4]:
                text = text + "\n" + str(count) + ". " + item
                count = count + 1

        return text

    def fallback_intent(self, text):
        normalized = clean_text(text)

        if "hola" in normalized or "buenas" in normalized or "saludos" in normalized:
            return "saludar"

        if "adios" in normalized or "hasta luego" in normalized:
            return "despedirse"

        if "que es" in normalized or "explicame" in normalized or "informacion" in normalized:
            return "buscar_informacion"

        if "recomend" in normalized or "proteg" in normalized or "prevenir" in normalized:
            return "solicitar_recomendaciones"

        if "pasos" in normalized or "guia" in normalized:
            return "solicitar_pasos"

        if "categoria" in normalized or "tipo de ataque" in normalized:
            return "detectar_categoria"

        if "buenas practicas" in normalized:
            return "buenas_practicas"

        if len(normalized.split(" ")) > 10:
            return "explicar_caso_largo"

        return "reportar_problema"

    def contains_mobile_brand_or_model(self, text):
        normalized = clean_text(text)

        brands = self.mobile_models_data.get("brands", [])
        models = self.mobile_models_data.get("models", [])

        for brand in brands:
            if brand in normalized:
                return True

        for model in models:
            if model in normalized:
                return True

        return False

    def has_useful_problem_info(self, text):
        report_data = self.datasets["reportar_problema"]
        threats = report_data.get("threats", {})

        for threat_name in threats:
            threat_data = threats[threat_name]
            symptoms = threat_data.get("symptoms", [])

            for symptom in symptoms:
                term = symptom.get("term", "")

                if text_contains_term(text, term):
                    return True

        return False

    def should_use_mobile_brand_response(self, text):
        has_brand_or_model = self.contains_mobile_brand_or_model(text)
        has_problem_info = self.has_useful_problem_info(text)

        if has_brand_or_model is True and has_problem_info is False:
            return True
        else:
            return False

    def run(self):
        print(self.get_welcome_message())
        active = True

        while active:
            user_text = input("Tu: ").strip()

            if clean_text(user_text) == "salir":
                print(self.farewell_handler())
                active = False
            else:
                response = self.process_input(user_text)
                print("CyberBot:", response)



import tkinter as tk
from tkinter import messagebox


class CyberBotGUI:
    def __init__(self, bot):
        self.bot = bot
        self.window = tk.Tk()
        self.window.title("CyberBot")
        self.window.geometry("900x600")

        self.top_frame = tk.Frame(self.window)
        self.top_frame.pack(fill="x", padx=10, pady=10)

        self.title_label = tk.Label(
            self.top_frame,
            text="CyberBot - Asistente de ciberseguridad",
            font=("Arial", 16, "bold")
        )
        self.title_label.pack(side="left")

        self.reset_button = tk.Button(
            self.top_frame,
            text="Reiniciar",
            command=self.reset_chat
        )
        self.reset_button.pack(side="right", padx=5)

        self.clear_button = tk.Button(
            self.top_frame,
            text="Limpiar",
            command=self.clear_chat
        )
        self.clear_button.pack(side="right", padx=5)

        self.main_frame = tk.Frame(self.window)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.left_frame = tk.Frame(self.main_frame)
        self.left_frame.pack(side="left", fill="both", expand=True)

        self.right_frame = tk.Frame(self.main_frame, width=220)
        self.right_frame.pack(side="right", fill="y", padx=(10, 0))
        self.right_frame.pack_propagate(False)

        self.chat_area = tk.Text(self.left_frame, wrap="word", state="disabled")
        self.chat_area.pack(fill="both", expand=True)

        self.entry_frame = tk.Frame(self.left_frame)
        self.entry_frame.pack(fill="x", pady=(10, 0))

        self.entry = tk.Entry(self.entry_frame)
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", self.send_message_event)

        self.send_button = tk.Button(
            self.entry_frame,
            text="Enviar",
            command=self.send_message
        )
        self.send_button.pack(side="left", padx=(10, 0))

        self.status_title = tk.Label(
            self.right_frame,
            text="Estado",
            font=("Arial", 13, "bold")
        )
        self.status_title.pack(anchor="w", pady=(0, 10))

        self.status_text = tk.Text(self.right_frame, height=10, width=25, state="disabled")
        self.status_text.pack(fill="x")

        self.prompts_title = tk.Label(
            self.right_frame,
            text="Mensajes rapidos",
            font=("Arial", 13, "bold")
        )
        self.prompts_title.pack(anchor="w", pady=(15, 10))

        self.prompt_buttons = []
        prompts = [
            "Me han hackeado",
            "He recibido un correo sospechoso",
            "Mis archivos estan cifrados",
            "Que es el phishing",
            "Buenas practicas"
        ]

        for prompt in prompts:
            button = tk.Button(
                self.right_frame,
                text=prompt,
                anchor="w",
                command=lambda p=prompt: self.use_prompt(p)
            )
            button.pack(fill="x", pady=2)
            self.prompt_buttons.append(button)

        self.add_message("CyberBot", self.bot.get_welcome_message())
        self.update_status()

    def add_message(self, role, text):
        self.chat_area.config(state="normal")
        self.chat_area.insert("end", role + ": " + text + "\\n\\n")
        self.chat_area.config(state="disabled")
        self.chat_area.see("end")

    def send_message_event(self, event):
        self.send_message()

    def send_message(self):
        user_text = self.entry.get().strip()

        if user_text == "":
            messagebox.showinfo("CyberBot", "Escribe un mensaje.")
        else:
            self.add_message("Tú", user_text)
            self.entry.delete(0, "end")
            response = self.bot.process_input(user_text)
            self.add_message("CyberBot", response)
            self.update_status()

    def update_status(self):
        status = self.bot.get_status()
        text = "Amenaza: " + status["threat"]
        text = text + "\\nConfianza: " + status["confidence"]
        text = text + "\\nTurnos: " + status["turns"]
        text = text + "\\nHechos: " + status["facts"]

        self.status_text.config(state="normal")
        self.status_text.delete("1.0", "end")
        self.status_text.insert("1.0", text)
        self.status_text.config(state="disabled")

    def use_prompt(self, prompt):
        self.entry.delete(0, "end")
        self.entry.insert(0, prompt)

    def clear_chat(self):
        self.chat_area.config(state="normal")
        self.chat_area.delete("1.0", "end")
        self.chat_area.config(state="disabled")
        self.add_message("CyberBot", self.bot.get_welcome_message())
        self.update_status()

    def reset_chat(self):
        response = self.bot.reset_session()
        self.chat_area.config(state="normal")
        self.chat_area.delete("1.0", "end")
        self.chat_area.config(state="disabled")
        self.add_message("CyberBot", response)
        self.add_message("CyberBot", self.bot.get_welcome_message())
        self.update_status()

    def run(self):
        self.window.mainloop()
