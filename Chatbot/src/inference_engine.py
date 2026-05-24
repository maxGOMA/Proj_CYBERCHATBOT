from collections import defaultdict

from src.nlp_utils import all_terms_in_text
from src.nlp_utils import build_hybrid_vector_model
from src.nlp_utils import clean_text
from src.nlp_utils import compute_hybrid_similarity_scores
from src.nlp_utils import preprocess_sentence
from src.nlp_utils import token_overlap_ratio


INTENT_THRESHOLD = 0.16
THREAT_THRESHOLD = 0.18
INFO_THRESHOLD = 0.14

THREAT_PROFILE_HINTS = {
    "phishing": [
        "correo urgente",
        "pagina clonada",
        "mensaje del banco",
        "suplantacion de identidad",
        "sms sospechoso",
    ],
    "ransomware": [
        "pantalla de rescate",
        "archivos no abren",
        "pago en criptomonedas",
        "equipo bloqueado",
    ],
    "ddos": [
        "muchas conexiones simultaneas",
        "servidor saturado",
        "ataque de trafico",
    ],
    "sql_injection": [
        "consulta manipulada",
        "formulario vulnerable",
        "filtracion de base de datos",
    ],
    "malware": [
        "pc lento",
        "equipo lento",
        "uso de cpu alto",
        "ventilador a tope",
        "se calienta mucho",
        "mineria de criptomonedas",
        "minando criptomonedas",
        "troyano minero",
        "consumo anormal de recursos",
    ],
    "man_in_the_middle": [
        "red wifi sospechosa",
        "certificado del navegador",
        "conexion interceptada",
    ],
    "brute_force": [
        "muchos intentos de acceso",
        "pruebas de contrasena",
        "bloqueos de cuenta",
    ],
    "insider_threat": [
        "empleado con acceso",
        "fuga interna",
        "copia de datos",
        "uso indebido de privilegios",
    ],
}


def _sort_scores(scores, priority_lookup=None):
    priority_lookup = priority_lookup or {}
    return dict(
        sorted(
            scores.items(),
            key=lambda item: (
                item[1],
                priority_lookup.get(item[0], 0),
            ),
            reverse=True,
        )
    )


def build_intent_model(examples_by_intent):
    example_documents = []
    example_labels = []
    intent_documents = []
    intent_labels = []

    for intent_name, examples in examples_by_intent.items():
        valid_examples = []

        for example in examples:
            processed_example = preprocess_sentence(example)
            if not processed_example:
                continue

            valid_examples.append(example)
            example_documents.append(example)
            example_labels.append(intent_name)

        if valid_examples:
            intent_documents.append(" ".join(valid_examples))
            intent_labels.append(intent_name)

    return {
        "example_labels": example_labels,
        "example_model": build_hybrid_vector_model(example_documents),
        "intent_labels": intent_labels,
        "intent_model": build_hybrid_vector_model(intent_documents),
        "intents": intent_labels,
    }


def build_threat_model(dataset):
    documents = []
    labels = []
    priorities = {}

    for threat_name, threat_data in dataset.get("threats", {}).items():
        parts = [
            threat_name.replace("_", " "),
            threat_data.get("description", ""),
            threat_data.get("severity", ""),
        ]

        for symptom in threat_data.get("symptoms", []):
            term = symptom.get("term", "")
            weight = max(1, int(symptom.get("specificity", 1)))
            parts.extend([term] * weight)

        parts.extend(THREAT_PROFILE_HINTS.get(threat_name, []))
        documents.append(" ".join(parts))
        labels.append(threat_name)
        priorities[threat_name] = int(threat_data.get("priority", 0))

    return {
        "labels": labels,
        "priorities": priorities,
        "vector_model": build_hybrid_vector_model(documents),
    }


def build_info_model(dataset):
    documents = []
    labels = []

    for threat_name, threat_data in dataset.get("threats", {}).items():
        parts = [
            threat_name.replace("_", " "),
            threat_data.get("title", ""),
            threat_data.get("summary", ""),
            threat_data.get("detail", ""),
        ]
        parts.extend(threat_data.get("keywords", []))
        documents.append(" ".join(parts))
        labels.append(threat_name)

    return {
        "labels": labels,
        "vector_model": build_hybrid_vector_model(documents),
    }


def detect_intent(user_text, model):
    intents = model.get("intents", [])
    if not intents:
        return None, 0.0

    example_scores = compute_hybrid_similarity_scores(
        user_text,
        model.get("example_model"),
    )
    centroid_scores = compute_hybrid_similarity_scores(
        user_text,
        model.get("intent_model"),
    )

    best_by_example = defaultdict(float)

    for label, score in zip(model.get("example_labels", []), example_scores):
        best_by_example[label] = max(best_by_example[label], float(score))

    scores = {}

    for label, score in zip(model.get("intent_labels", []), centroid_scores):
        centroid_score = float(score)
        example_score = best_by_example.get(label, 0.0)
        scores[label] = (centroid_score * 0.55) + (example_score * 0.45)

    if not scores:
        return None, 0.0

    ordered_scores = _sort_scores(scores)
    best_intent = next(iter(ordered_scores))
    return best_intent, float(ordered_scores[best_intent])


def _score_symptoms(user_text, threat_data):
    matched_terms = []
    accumulated = 0.0
    total_weight = 0.0

    for symptom in threat_data.get("symptoms", []):
        symptom_text = symptom.get("term", "")
        specificity = float(symptom.get("specificity", 1))
        total_weight += specificity

        if all_terms_in_text(user_text, symptom_text):
            accumulated += specificity
            matched_terms.append(symptom_text)
            continue

        overlap = token_overlap_ratio(user_text, symptom_text)
        if overlap >= 0.66:
            accumulated += specificity * overlap * 0.85
            matched_terms.append(symptom_text)

    if total_weight == 0:
        return 0.0, []

    return accumulated / total_weight, matched_terms


def _keyword_bonus(user_text, keywords, scale):
    if not keywords:
        return 0.0

    matches = 0

    for keyword in keywords:
        if all_terms_in_text(user_text, keyword) or token_overlap_ratio(user_text, keyword) >= 0.75:
            matches += 1

    normalizer = max(1, min(len(keywords), 4))
    return min(scale, (matches / normalizer) * scale)


def _score_threat_candidates(user_text, dataset, model):
    labels = model.get("labels", [])
    semantic_scores = compute_hybrid_similarity_scores(
        user_text,
        model.get("vector_model"),
    )

    scores = {}
    evidence = {}

    for index, threat_name in enumerate(labels):
        threat_data = dataset["threats"][threat_name]
        symptom_score, matched_terms = _score_symptoms(user_text, threat_data)
        semantic_score = (
            float(semantic_scores[index]) if index < len(semantic_scores) else 0.0
        )
        name_bonus = 0.18 if all_terms_in_text(user_text, threat_name.replace("_", " ")) else 0.0
        hint_bonus = _keyword_bonus(
            user_text,
            THREAT_PROFILE_HINTS.get(threat_name, []),
            scale=0.12,
        )
        priority_bonus = min(0.08, int(threat_data.get("priority", 0)) / 100)
        combined_score = min(
            1.0,
            (symptom_score * 0.62)
            + (semantic_score * 0.28)
            + hint_bonus
            + name_bonus
            + priority_bonus,
        )

        if combined_score >= THREAT_THRESHOLD * 0.5 or matched_terms or semantic_score >= 0.08:
            scores[threat_name] = round(combined_score, 4)
            evidence[threat_name] = {
                "matched_terms": matched_terms[:5],
                "semantic_score": round(semantic_score, 4),
                "symptom_score": round(symptom_score, 4),
            }

    ordered_scores = _sort_scores(scores, model.get("priorities"))
    return ordered_scores, evidence


def detect_threat(user_text, dataset, model):
    ordered_scores, evidence = _score_threat_candidates(user_text, dataset, model)

    if not ordered_scores:
        return None, 0.0, {}, {}

    best_threat = next(iter(ordered_scores))
    best_score = ordered_scores[best_threat]
    best_matches = evidence.get(best_threat, {}).get("matched_terms", [])

    if best_score < THREAT_THRESHOLD and len(best_matches) < 2:
        return None, best_score, ordered_scores, evidence

    return best_threat, best_score, ordered_scores, evidence


def detect_threat_from_history(known_facts, dataset, model):
    if not known_facts:
        return None, 0.0, {}, {}

    combined_scores = defaultdict(float)
    appearances = defaultdict(int)
    merged_terms = defaultdict(set)

    joined_facts = " ".join(known_facts)
    joined_scores, joined_evidence = _score_threat_candidates(joined_facts, dataset, model)

    for threat_name, score in joined_scores.items():
        combined_scores[threat_name] += score * 1.15
        appearances[threat_name] += 1
        merged_terms[threat_name].update(
            joined_evidence.get(threat_name, {}).get("matched_terms", [])
        )

    for fact in known_facts:
        fact_scores, fact_evidence = _score_threat_candidates(fact, dataset, model)
        for threat_name, score in fact_scores.items():
            combined_scores[threat_name] += score
            appearances[threat_name] += 1
            merged_terms[threat_name].update(
                fact_evidence.get(threat_name, {}).get("matched_terms", [])
            )

    if not combined_scores:
        return None, 0.0, {}, {}

    normalized_scores = {}

    for threat_name, total_score in combined_scores.items():
        repeat_bonus = min(0.16, appearances[threat_name] * 0.04)
        normalized_scores[threat_name] = min(
            1.0,
            (total_score / max(1, len(known_facts) + 1)) + repeat_bonus,
        )

    ordered_scores = _sort_scores(normalized_scores, model.get("priorities"))
    best_threat = next(iter(ordered_scores))
    best_score = ordered_scores[best_threat]
    evidence = {
        threat_name: {"matched_terms": sorted(terms)}
        for threat_name, terms in merged_terms.items()
    }

    if best_score < THREAT_THRESHOLD and len(evidence.get(best_threat, {}).get("matched_terms", [])) < 2:
        return None, best_score, ordered_scores, evidence

    return best_threat, best_score, ordered_scores, evidence


def detect_info_threat(user_text, dataset, model):
    labels = model.get("labels", [])
    if not labels:
        return None

    semantic_scores = compute_hybrid_similarity_scores(
        user_text,
        model.get("vector_model"),
    )
    scores = {}

    for index, threat_name in enumerate(labels):
        threat_data = dataset["threats"][threat_name]
        semantic_score = (
            float(semantic_scores[index]) if index < len(semantic_scores) else 0.0
        )
        keyword_bonus = _keyword_bonus(
            user_text,
            threat_data.get("keywords", []),
            scale=0.28,
        )
        name_bonus = 0.16 if all_terms_in_text(user_text, threat_name.replace("_", " ")) else 0.0
        scores[threat_name] = semantic_score * 0.6 + keyword_bonus + name_bonus

    ordered_scores = _sort_scores(scores)
    best_threat = next(iter(ordered_scores))
    best_score = ordered_scores[best_threat]

    if best_score < INFO_THRESHOLD:
        return None

    return best_threat


def classify_yes_no(user_text, dataset):
    normalized = clean_text(user_text)
    if not normalized:
        return "unknown"

    negative_options = sorted(
        (clean_text(option) for option in dataset.get("negations", [])),
        key=len,
        reverse=True,
    )
    positive_options = sorted(
        (clean_text(option) for option in dataset.get("confirmations", [])),
        key=len,
        reverse=True,
    )

    for option_text in negative_options:
        if normalized == option_text or option_text in normalized:
            return "no"

    for option_text in positive_options:
        if normalized == option_text or option_text in normalized:
            return "yes"

    return "unknown"
