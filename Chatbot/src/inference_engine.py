from sklearn.feature_extraction.text import CountVectorizer

from src.nlp_utils import count_common_words
from src.nlp_utils import text_contains_term
from src.nlp_utils import clean_text

INTENT_THRESHOLD = 1
THREAT_THRESHOLD = 1
INFO_THRESHOLD = 1


def build_intent_model(examples_by_intent):
    texts = []
    labels = []
    for intent_name in examples_by_intent:
        examples = examples_by_intent[intent_name]
        for example in examples:
            clean_example = clean_text(example)
            texts.append(clean_example)
            labels.append(intent_name)

    vectorizer = CountVectorizer()
    matrix = vectorizer.fit_transform(texts)

    model = {}
    model["examples_by_intent"] = examples_by_intent
    model["vectorizer"] = vectorizer
    model["matrix"] = matrix
    model["labels"] = labels

    return model


def build_threat_model(report_dataset):
    return report_dataset


def build_info_model(info_dataset):
    return info_dataset


def detect_intent(user_text, intent_model):
    vectorizer = intent_model["vectorizer"]
    matrix = intent_model["matrix"]
    labels = intent_model["labels"]

    clean_user_text = clean_text(user_text)
    user_vector = vectorizer.transform([clean_user_text])
    user_array = user_vector.toarray()[0]
    best_intent = None
    best_score = 0

    i = 0
    while i < len(labels):
        example_array = matrix[i].toarray()[0]
        score = 0
        j = 0
        while j < len(user_array):
            if user_array[j] > 0 and example_array[j] > 0:
                score = score + 1
            j = j + 1
        if score > best_score:
            best_score = score
            best_intent = labels[i]

        i = i + 1

    return best_intent, best_score


def classify_yes_no(user_text, dataset):
    confirmations = dataset.get("confirmations", [])
    negations = dataset.get("negations", [])

    for word in confirmations:
        if text_contains_term(user_text, word):
            return "yes"

    for word in negations:
        if text_contains_term(user_text, word):
            return "no"
    return "unknown"


def detect_threat(user_text, report_dataset, threat_model=None):
    threats = report_dataset.get("threats", {})
    all_scores = {}
    evidence = {}
    best_threat = None
    best_score = 0

    for threat_name in threats:
        threat_data = threats[threat_name]
        symptoms = threat_data.get("symptoms", [])
        score = 0
        matched_terms = []

        for symptom in symptoms:
            term = symptom.get("term", "")
            specificity = symptom.get("specificity", 1)

            if text_contains_term(user_text, term):
                score = score + specificity
                matched_terms.append(term)
        if score > 0:
            priority = threat_data.get("priority", 0)
            score = score + (priority / 100.0)
            all_scores[threat_name] = round(score, 2)
            evidence[threat_name] = {"matched_terms": matched_terms}
            if score > best_score:
                best_score = score
                best_threat = threat_name

    if best_threat is None:
        return None, 0.0, all_scores, evidence

    sorted_scores = sort_scores(all_scores)
    confidence = best_score / 10.0
    return best_threat, confidence, sorted_scores, evidence


def detect_threat_from_history(known_facts, report_dataset, threat_model=None):
    text = " ".join(known_facts)
    return detect_threat(text, report_dataset, threat_model)


def detect_info_threat(user_text, info_dataset, info_model=None):
    threats = info_dataset.get("threats", {})
    best_threat = None
    best_score = 0

    for threat_name in threats:
        threat_data = threats[threat_name]
        score = 0

        if text_contains_term(user_text, threat_name):
            score = score + 3

        title = threat_data.get("title", "")
        if text_contains_term(user_text, title):
            score = score + 2

        keywords = threat_data.get("keywords", [])
        for keyword in keywords:
            if text_contains_term(user_text, keyword):
                score = score + 1

        if score > best_score:
            best_score = score
            best_threat = threat_name

    if best_score < INFO_THRESHOLD:
        return None
    return best_threat


def sort_scores(scores):
    items = list(scores.items())
    items.sort(key=lambda item: item[1], reverse=True)
    sorted_dict = {}
    for item in items:
        sorted_dict[item[0]] = item[1]

    return sorted_dict