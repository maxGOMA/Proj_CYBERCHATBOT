from src.nlp_utils import all_terms_in_text, build_tfidf_model, compute_similarity_scores
from src.nlp_utils import preprocess_sentence


INTENT_THRESHOLD = 0.10
INFO_THRESHOLD = 1


def build_intent_model(examples_by_intent):
    documents = []
    labels = []

    for intent_name, examples in examples_by_intent.items():
        for example in examples:
            processed_example = preprocess_sentence(example)
            if processed_example:
                documents.append(processed_example)
                labels.append(intent_name)

    if not documents:
        return {
            "vectorizer": None,
            "matrix": None,
            "labels": [],
        }

    vectorizer, matrix = build_tfidf_model(documents)

    return {
        "vectorizer": vectorizer,
        "matrix": matrix,
        "labels": labels,
    }


def detect_intent(user_text, model):
    labels = model.get("labels", [])
    if not labels:
        return None, 0.0

    scores = compute_similarity_scores(
        user_text,
        model["vectorizer"],
        model["matrix"],
    )

    best_index = int(scores.argmax())
    best_intent = labels[best_index]
    best_score = float(scores[best_index])
    return best_intent, best_score


def detect_threat(user_text, dataset):
    threats = dataset.get("threats", {})
    scores = {}

    for threat_name, threat_data in threats.items():
        total_score = 0

        for symptom in threat_data.get("symptoms", []):
            symptom_text = symptom.get("term", "")
            specificity = int(symptom.get("specificity", 1))

            if all_terms_in_text(user_text, symptom_text):
                total_score += specificity

        if total_score > 0:
            scores[threat_name] = total_score

    if not scores:
        return None, 0, {}

    ordered_scores = dict(
        sorted(scores.items(), key=lambda item: item[1], reverse=True)
    )
    best_threat = next(iter(ordered_scores))
    best_score = ordered_scores[best_threat]
    return best_threat, best_score, ordered_scores


def detect_threat_from_history(known_facts, dataset):
    total_scores = {}

    for fact in known_facts:
        threat, score, _ = detect_threat(fact, dataset)
        if threat:
            total_scores[threat] = total_scores.get(threat, 0) + score

    if not total_scores:
        return None, 0, {}

    ordered_scores = dict(
        sorted(total_scores.items(), key=lambda item: item[1], reverse=True)
    )
    best_threat = next(iter(ordered_scores))
    best_score = ordered_scores[best_threat]
    return best_threat, best_score, ordered_scores


def detect_info_threat(user_text, dataset):
    threats = dataset.get("threats", {})
    best_threat = None
    best_score = 0

    for threat_name, threat_data in threats.items():
        current_score = 0

        for keyword in threat_data.get("keywords", []):
            if all_terms_in_text(user_text, keyword):
                current_score += 1

        if current_score > best_score:
            best_score = current_score
            best_threat = threat_name

    if best_score < INFO_THRESHOLD:
        return None

    return best_threat


def classify_yes_no(user_text, dataset):
    clean_text = user_text.strip().lower()

    for option in dataset.get("confirmations", []):
        option_text = option.lower()
        if clean_text == option_text or option_text in clean_text:
            return "yes"

    for option in dataset.get("negations", []):
        option_text = option.lower()
        if clean_text == option_text or option_text in clean_text:
            return "no"

    return "unknown"
