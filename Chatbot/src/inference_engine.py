from src.nlp_utils import full_pipeline, tfidf_vector, cosine_similarity

# Umbral mínimo de score para emitir diagnóstico
MIN_THRESHOLD = 0.01


class InferenceEngine:

    BONUS_FACTOR = 2.0   # cuanto pesa la priority en el score final.

    def __init__(self, idf):
        self.idf = idf

    # evalua la peticion del usuario y asigna una respuesta debida:
    def evaluate(self, user_text, dataset):        
        threats = dataset.get("threats", {})
        if not threats:
            return None, 0.0, {}

        # proceso el texto:
        user_lemmas  = full_pipeline(user_text)
        user_text_joined = " ".join(user_lemmas)
        all_scores   = {}

        # paso por todos los threats y busco el que mas se ajusta:
        for threat_name, threat_data in threats.items():
            specificity_total = self._compute_specificity(user_text_joined, threat_data)
            priority = threat_data.get("priority", 5)
            priority_bonus = (priority / 10.0) * self.BONUS_FACTOR

            # solo se suma el bonus si hay al menos una coincidencia:
            if specificity_total > 0:
                score = specificity_total + priority_bonus
            else:
                score = 0.0

            if score > 0:
                all_scores[threat_name] = round(score, 4)

        if not all_scores:
            return None, 0.0, {}

        # me guardo la amenaza que ha tenido la puntuacion mas alta:
        best_threat = max(all_scores, key=all_scores.get)
        # me guardo la puntuacion mas alta:
        best_score  = all_scores[best_threat]

        if best_score < MIN_THRESHOLD:
            return None, best_score, all_scores

        items = all_scores.items()
        items_list = list(items)

        # ordenar manualmente por el valor:
        items_list.sort(key=lambda pair: pair[1], reverse=True)

        sorted_scores = {}
        for pair in items_list:
            key = pair[0]
            value = pair[1]
            sorted_scores[key] = value

        return best_threat, best_score, sorted_scores

    # suma los valores de specificity de cada sintoma que coincide con el texto del usuario:
    def _compute_specificity(self, user_text_joined, threat_data):
        total = 0.0
        symptoms = threat_data.get("symptoms", [])

        for symptom_entry in symptoms:
            term = symptom_entry.get("term", "")
            specificity = symptom_entry.get("specificity", 1)

            # proceso el termino con el mismo pipeline que el input:
            term_lemmas = full_pipeline(term)

            # compruebo si todos los lemas del termino estan en el input:
            if term_lemmas:
                all_present = True

                for lemma in term_lemmas:
                    if lemma not in user_text_joined:
                        all_present = False
                        break

                if all_present:
                    total += specificity

        return total

    # busca la amenaza mas relevante en el dataset de informacion usando similitud coseno TF-IDF sobre las keywords de cada amenaza
    def find_in_info_dataset(self, user_text, dataset):
        threats = dataset.get("threats", {})
        if not threats:
            return None

        user_vec = tfidf_vector(full_pipeline(user_text), self.idf)
        best, best_score = None, -1.0

        for threat_name, threat_data in threats.items():
            keywords = threat_data.get("keywords", [])
            keyword_lemmas = []
            for kw in keywords:
                keyword_lemmas.extend(full_pipeline(kw))
            kw_vec = tfidf_vector(keyword_lemmas, self.idf)
            score  = cosine_similarity(user_vec, kw_vec)
            if score > best_score:
                best_score = score
                best       = threat_name

        return best if best_score > 0.01 else None

    # acumula hechos de múltiples turnos y devuelve todas las amenazas activadas:
    def forward_chaining(self, known_facts, dataset):    
        activated = {}
        for fact in known_facts:
            threat, score, _ = self.evaluate(fact, dataset)
            if threat:
                activated[threat] = activated.get(threat, 0) + score
        
        items_list = list(activated.items())

        # ordenar manualmente por el valor:
        items_list.sort(key=lambda pair: pair[1], reverse=True)

        sorted_dict = {}
        for pair in items_list:
            key = pair[0]
            value = pair[1]
            sorted_dict[key] = value

        return sorted_dict