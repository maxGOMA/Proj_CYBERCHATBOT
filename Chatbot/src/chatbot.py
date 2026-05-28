import random
import re
from src.session import Session
from src.external_qa import ApifyStackOverflowClient, format_question_details, format_question_list
import src.dataset_loader as dl

THREAT_NAMES = {
    "phishing":"Phishing",
    "ransomware":"Ransomware",
    "ddos":"Ataque DDoS",
    "sql_injection":"Inyección SQL",
    "malware":"Malware / Virus",
    "man_in_the_middle":"Man-in-the-Middle",              
    "brute_force":"Fuerza Bruta",
    "insider_threat":"Amenaza Interna"
}

# umbral minimo de similitud coseno para aceptar una intencion:
INTENT_THRESHOLD = 0.05


class Chatbot:
    def __init__(self, intent_detector, inference_engine, idf):
        self.detector = intent_detector
        self.engine   = inference_engine
        self.idf      = idf
        self.session  = Session()
        self.external_client = ApifyStackOverflowClient()

        # mapa para guardar la intencion con la funcion que lo procesa asociada:
        self.handlers = {
            "saludar":self.greetHandler,
            "despedirse":self.farewellHandler,
            "pedir_ayuda":self.helpHandler,
            "reportar_problema":self.reportProblemHandler,
            "buscar_informacion":self.informationRequestHandler,
            "solicitar_recomendaciones":self.recommendationsRequestHandler,
            "detectar_categoria":self.categoryHandler,
            "confirmar_negar":self.confirmDenyHandler,
            "solicitar_pasos":self.stepsToFollowHandler,
            "solicitar_diagnostico":self.reportProblemHandler,   
            #"explicar_caso_largo":self._h_caso_largo,
            "buenas_practicas":self.goodPracticesHandler,            
        }

    def process_input(self, user_text):
        # quito los espacios de la cadena y compruebo si el usuario ha escrito algo:
        if not user_text.strip():
            return "No he recibido ningún texto. ¿En qué puedo ayudarte?"

        # registro el mensaje para guardar el registro de lo que escribe el usuario:
        self.session.add_message("user", user_text)

        # si el usuario esta eligiendo una pregunta externa, no detecto intencion:
        if self.session.awaiting_external_choice:
            response = self.externalChoiceHandler(user_text)
            self.session.add_message("bot", response)
            return response

        intent, score = self.detector(user_text)

        # en el caso de que la puntuacion sea muy baja, reporto el problema
        if score < INTENT_THRESHOLD:
            intent = "reportar_problema"

        # me guardo la intencion en la sesion:
        self.session.set_intent(intent)

        # obtengo la funcion que va a procesar el texto de usuario en base a su intencion:
        if intent in self.handlers:
            handler = self.handlers[intent]
        else:
            handler = self.reportProblemHandler

        # obtengo la respuesta:
        response = handler(user_text)
        # añado el mensaje final de respuesta:
        self.session.add_message("bot", response)
        return response

    # manejo los saludos (random porque no importa cual se proporciona)
    def greetHandler(self, text):
        data = dl.load("saludar")
        return random.choice(data["responses"])
    
    # manejo la despedida (random porque no importa cual se proporciona)
    def farewellHandler(self, text):
        data = dl.load("despedirse")
        return random.choice(data["responses"])

    # en caso de que la intencion sea pedir ayuda cargo la respuesta asociada:
    def helpHandler(self, text):
        # cargo el dataset de ayuda:
        data = dl.load("pedir_ayuda")
        # obtengo la respuesta:
        r    = data["response"]
        # creo todo el mensaje:
        lines = [r["intro"]]
        for opt in r["options"]:
            lines.append(f"  • {opt}")
        return "\n".join(lines)

    # en el caso de que el usuario tenga un problema y necesite informacion:
    def reportProblemHandler(self, text):
        # cargo el dataset relacionado:
        dataset = dl.load("reportar_problema")
        # evaluo la mejor respuesta posible:
        threat, score, all_scores = self.engine.evaluate(text, dataset)
        # actualizo los nuevos valores en la sesion:
        self.session.update_facts(text)

        #  si no hay ninguna amenaza, miro los mensajes registrados:
        if threat is None:
            if len(self.session.known_facts) > 1:
                accumulated = self.engine.forward_chaining(self.session.known_facts, dataset)
                if accumulated:
                    # obtener la primera clave de forma clásica
                    keys = accumulated.keys()
                    first_key = list(keys)[0]

                    threat = first_key
                    score = accumulated[first_key]

        # en caso de que no se considere que sea una amenaza:
        if threat is None:
            return self.noDiagnosis()

        # establezco la amenaza en cuestion en la sesion:
        self.session.set_threat(threat)
        threat_data = dataset["threats"][threat]
        return self.formatDiagnosis(threat, threat_data, score, all_scores)

    # en caso de que la intencion del usuario sea conocer mas un problema en concreto:
    def informationRequestHandler(self, text):
        # cargo el dataset relacionado:
        dataset = dl.load("buscar_informacion")
        # busco la mejor respuesta con el motor de inferencia:
        threat  = self.engine.find_in_info_dataset(text, dataset)

        # en caso de que no haya detectado una respuesta:
        if not threat:
            return self.externalInfoFallback(text)

        # obtengo la informacion relacionada a la amenaza detectada para explicarla al usuario:
        t     = dataset["threats"][threat]
        name  = THREAT_NAMES.get(threat, threat)
        lines = [
            name,
            f"\nResumen: {t['summary']}",
            f"\nDetalle:\n{t['detail']}",
            "\n¿Quieres recomendaciones, pasos de respuesta o más información?"
        ]
        return "\n".join(lines)

    def externalInfoFallback(self, text):
        if not self.external_client.is_configured():
            return (
                "No he encontrado informacion sobre ese tema.\n"
                "Si quieres que consulte Stack Overflow, configura la variable APIFY_TOKEN."
            )

        try:
            results = self.external_client.search_questions(text)
        except Exception as exc:
            return (
                "No he encontrado informacion sobre ese tema.\n"
                "Ahora mismo no puedo consultar la API externa."
            )

        if not results:
            return (
                "No he encontrado informacion sobre ese tema.\n"
                "Prueba con una consulta mas concreta."
            )

        self.session.set_external_results(text, results)
        return format_question_list(results)

    def externalChoiceHandler(self, text):
        clean = text.strip().lower()

        if self._is_external_back_command(clean):
            self.session.clear_external_results()
            return "De acuerdo. Haz otra consulta cuando quieras."

        choice = self._parse_external_choice(clean)
        results = self.session.external_results

        if choice is None:
            return (
                "No he entendido tu eleccion.\n"
                "Responde con un numero o escribe 'otra consulta'."
            )

        if not results:
            self.session.clear_external_results()
            return "No tengo resultados almacenados. Haz otra consulta."

        if choice < 1 or choice > len(results):
            return f"Elige un numero entre 1 y {len(results)}."

        item = results[choice - 1]
        self.session.clear_external_results()
        return format_question_details(item)

    def _parse_external_choice(self, text):
        match = re.search(r"\d+", text)
        if not match:
            return None
        return int(match.group(0))

    def _is_external_back_command(self, text):
        if text in {"otra consulta", "otra", "volver", "volver atras", "atras", "cancelar"}:
            return True
        if text.startswith("otra consulta"):
            return True
        if text.startswith("volver"):
            return True
        return False

    # en caso de que el usuario quiera protegerse mas:
    def recommendationsRequestHandler(self, text):
        # cargo los datasets relacionados:
        ds_rec  = dl.load("solicitar_recomendaciones")
        ds_rep  = dl.load("reportar_problema")
        threat, _, _ = self.engine.evaluate(text, ds_rep)

        # si no detecta amenaza concreta, usar la ultima de la sesion:
        if not threat:
            threat = self.session.last_threat

        if threat and threat in ds_rec.get("by_threat", {}):
            name  = THREAT_NAMES.get(threat, threat)
            recs  = ds_rec["by_threat"][threat]
            lines = [f"Recomendaciones para {name}:"]
            for i, r in enumerate(recs, 1):
                lines.append(f"  {i}. {r}")
            return "\n".join(lines)

        # recomendaciones generales:
        tips  = ds_rec.get("general", [])
        lines = ["Buenas practicas generales:"]
        for i, t in enumerate(tips, 1):
            lines.append(f"  {i}. {t}")
        return "\n".join(lines)

    def categoryHandler(self, text):
        ds_cat = dl.load("detectar_categoria")
        ds_rep = dl.load("reportar_problema")
        threat, _, _ = self.engine.evaluate(text, ds_rep)
 
        if not threat:
            threat = self.session.last_threat
 
        if not threat:
            return "No he identificado una amenaza concreta. Describe el problema primero."
 
        categories = ds_cat.get("categories", {})
        descs      = ds_cat.get("category_descriptions", {})
        category = None
        for cat, threats in categories.items():
            if threat in threats:
                category = cat
                break
 
        if not category:
            return "No he podido clasificar la amenaza en una categoria."
 
        name = THREAT_NAMES.get(threat, threat)
        return (f"{name} pertenece a la categoria: {category.upper()}\n"
                f"{descs.get(category, '')}")

    def confirmDenyHandler(self, text):
        data = dl.load("confirmar_negar")
        clean = text.lower().strip()
        if any(c in clean for c in data["confirmations"]):
            return random.choice(data["responses"]["confirm"])
        return random.choice(data["responses"]["deny"])

    def stepsToFollowHandler(self, text):
        ds_steps = dl.load("solicitar_pasos")
        ds_rep = dl.load("reportar_problema")
        threat, _, _ = self.engine.evaluate(text, ds_rep)
 
        if not threat:
            threat = self.session.last_threat
 
        steps = ds_steps.get("steps", {})
        if not threat or threat not in steps:
            return (
                "Necesito saber que amenaza quieres resolver.\n"
                "Describe el problema y luego pide los pasos."
            )
 
        name  = THREAT_NAMES.get(threat, threat)
        lines = [f"Pasos para responder a {name}:"]
        for step in steps[threat]:
            lines.append(f"  {step}")
        return "\n".join(lines)

    def goodPracticesHandler(self, text):
        data = dl.load("buenas_practicas")
        lines = ["Buenas practicas de ciberseguridad:"]
        for p in data.get("practices", []):
            lines.append(f"\n- {p['title']}")
            lines.append(f"  {p['detail']}")
        return "\n".join(lines)

    def noDiagnosis(self):
        if self.session.turn_count > 2:
            return (
                "No he podido identificar la amenaza.\n"
                "Puedes darme mas detalles: mensajes en pantalla, "
                "que ha dejado de funcionar, cuando empezo?"
            )
        return (
            "No he detectado ninguna amenaza conocida.\n"
            "Prueba describiendo sintomas concretos, por ejemplo:\n"
            "  - 'Mis archivos tienen extension rara y me piden bitcoin'\n"
            "  - 'Hay muchos intentos fallidos de login'\n"
            "  - 'El antivirus detecto un troyano'"
        )

    # funcion para darle formato a la respuesta que se le da al usuario:
    def formatDiagnosis(self, threat, threat_data, score, all_scores):
        name     = THREAT_NAMES.get(threat, threat)
        severity = threat_data.get("severity", "?")
        sev_labels = {"critica": "CRITICA", "alta": "ALTA", "media": "MEDIA"}
        label = sev_labels.get(severity, severity.upper())
 
        lines = [
            f"Amenaza identificada: {name}",
            f"Puntuacion: {score:.2f} | Severidad: {label}",
            f"\nDescripcion: {threat_data.get('description', '')}",
        ]
 
        if len(all_scores) > 1:
            
            others = []

            items = list(all_scores.items())[1:3]

            for pair in items:
                t = pair[0]
                s = pair[1]

                name = THREAT_NAMES.get(t, t)
                formatted_score = "%.2f" % s

                text = name + " (" + formatted_score + ")"
                others.append(text)

            lines.append(f"Otras posibles: {', '.join(others)}")
 
        lines.append("\nRecomendaciones:")
        for i, r in enumerate(threat_data.get("recommendations", []), 1):
            lines.append(f"  {i}. {r}")
 
        lines.append("\nQuieres los pasos detallados, mas informacion o tienes otro problema?")
        return "\n".join(lines)

    # bucle principal:
    def run(self):
        # muestro el mensaje inicial de bienvenida al usuario:
        print("\n" + "="*55)
        print("       CYBERBOT - Sistema Experto en Ciberseguridad")
        print("="*55)
        print("Escribe 'ayuda' para ver las opciones.\n")
        
        # bucle principal para ejecutar el chatbot todo lo que dure la conversacion:
        while True:
            try:
                # leo el input de la pantalla del usuario:
                user_input = input("Tu: ").strip()
                # en caso de que el usuario no haya escrito nada:
                if not user_input:
                    continue
                # compruebo si el usuario ha introducido alguna palabra para salir del sistema:
                if user_input.lower() in ["salir", "exit", "quit"]:
                    # obtengo la intencion del usuario y cargo el dataset relaconado:
                    data = dl.load("despedirse")
                    # devuelvo una respuesta random del dataset ya que tienen todas el mismo significado:
                    print(f"\nCyberBot: {random.choice(data['responses'])}\n")
                    break
                # compruebo si el usuario quiere reiniciar el chatbot:
                if user_input.lower() in ["reset", "reiniciar"]:
                    # reseteo el sistema:
                    self.session.reset()
                    print("\nCyberBot: Sesion reiniciada.\n")
                    continue
                # en caso de que no sea ninguno de los casos anteriores, proceso el texto introducido:
                response = self.process_input(user_input)
                print(f"\nCyberBot: {response}\n")
            except KeyboardInterrupt:
                # se ha detectado una interrupcion en el sistema:
                print("\n\nCyberBot: Hasta luego!\n")
                break
            except Exception as e:
                # se ha detectado una excepcion en el sistema:
                print(f"\nCyberBot: Error inesperado: {e}\n")