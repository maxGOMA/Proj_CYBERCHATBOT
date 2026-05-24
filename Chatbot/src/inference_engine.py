from sklearn.metrics.pairwise import cosine_similarity

from src.nlp_utils import build_tfidf_vectorizer, contains_all_terms, preprocess_text


MIN_DIAGNOSIS_SCORE = 0.18
MIN_INFO_SCORE = 0.12


class InferenceEngine:
    PRIORITY_WEIGHT = 0.03
    SYMPTOM_WEIGHT = 0.10

    def __init__(self):
        self._diagnosis_cache = {}
        self._info_cache = {}

    def evaluate(self, user_text, dataset):
        threats = dataset.get("threats", {})
        if not threats:
            return None, 0.0, {}

        cache = self._prepare_diagnosis_dataset(dataset)
        user_vector = cache["vectorizer"].transform([user_text])
        similarity_scores = cosine_similarity(user_vector, cache["matrix"])[0]
        user_tokens = preprocess_text(user_text)
        all_scores = {}

        for index, threat_name in enumerate(cache["labels"]):
            threat_data = threats[threat_name]
            similarity = float(similarity_scores[index])
            symptom_score = self._score_symptoms(user_tokens, threat_data)
            priority_bonus = float(threat_data.get("priority", 0)) * self.PRIORITY_WEIGHT
            total_score = similarity + (symptom_score * self.SYMPTOM_WEIGHT)

            if symptom_score > 0:
                total_score += priority_bonus
            elif similarity < MIN_INFO_SCORE:
                continue

            if total_score > 0:
                all_scores[threat_name] = round(total_score, 4)

        if not all_scores:
            return None, 0.0, {}

        sorted_scores = dict(
            sorted(all_scores.items(), key=lambda item: item[1], reverse=True)
        )
        best_threat, best_score = next(iter(sorted_scores.items()))

        if best_score < MIN_DIAGNOSIS_SCORE:
            return None, best_score, sorted_scores

        return best_threat, best_score, sorted_scores

    def find_in_info_dataset(self, user_text, dataset):
        threats = dataset.get("threats", {})
        if not threats:
            return None

        cache = self._prepare_info_dataset(dataset)
        user_vector = cache["vectorizer"].transform([user_text])
        scores = cosine_similarity(user_vector, cache["matrix"])[0]

        if scores.size == 0:
            return None

        best_index = int(scores.argmax())
        best_score = float(scores[best_index])

        if best_score < MIN_INFO_SCORE:
            return None

        return cache["labels"][best_index]

    def forward_chaining(self, known_facts, dataset):
        activated = {}

        for fact in known_facts:
            threat, score, _ = self.evaluate(fact, dataset)
            if threat:
                activated[threat] = round(activated.get(threat, 0.0) + score, 4)

        return dict(sorted(activated.items(), key=lambda item: item[1], reverse=True))

    def _prepare_diagnosis_dataset(self, dataset):
        cache_key = dataset.get("intent", "reportar_problema")
        if cache_key not in self._diagnosis_cache:
            threats = dataset.get("threats", {})
            labels = []
            documents = []

            for threat_name, threat_data in threats.items():
                labels.append(threat_name)
                documents.append(self._build_diagnosis_document(threat_name, threat_data))

            vectorizer = build_tfidf_vectorizer()
            matrix = vectorizer.fit_transform(documents)
            self._diagnosis_cache[cache_key] = {
                "labels": labels,
                "matrix": matrix,
                "vectorizer": vectorizer,
            }

        return self._diagnosis_cache[cache_key]

    def _prepare_info_dataset(self, dataset):
        cache_key = dataset.get("intent", "buscar_informacion")
        if cache_key not in self._info_cache:
            threats = dataset.get("threats", {})
            labels = []
            documents = []

            for threat_name, threat_data in threats.items():
                labels.append(threat_name)
                documents.append(self._build_info_document(threat_data))

            vectorizer = build_tfidf_vectorizer()
            matrix = vectorizer.fit_transform(documents)
            self._info_cache[cache_key] = {
                "labels": labels,
                "matrix": matrix,
                "vectorizer": vectorizer,
            }

        return self._info_cache[cache_key]

    def _score_symptoms(self, user_tokens, threat_data):
        total = 0.0

        for symptom in threat_data.get("symptoms", []):
            if contains_all_terms(user_tokens, symptom.get("term", "")):
                total += float(symptom.get("specificity", 1))

        return total

    def _build_diagnosis_document(self, threat_name, threat_data):
        parts = [threat_name.replace("_", " "), threat_data.get("description", "")]

        for symptom in threat_data.get("symptoms", []):
            term = symptom.get("term", "")
            repeat_count = max(1, int(symptom.get("specificity", 1)))
            parts.extend([term] * repeat_count)

        return " ".join(part for part in parts if part)

    def _build_info_document(self, threat_data):
        parts = [
            threat_data.get("title", ""),
            threat_data.get("summary", ""),
            threat_data.get("detail", ""),
            " ".join(threat_data.get("keywords", [])),
        ]
        return " ".join(part for part in parts if part)
