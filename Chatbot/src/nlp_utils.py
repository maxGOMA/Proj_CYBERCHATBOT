import re
import unicodedata

import nltk
import numpy as np
from nltk.corpus import stopwords
from nltk.stem.snowball import SnowballStemmer
from nltk.tokenize import word_tokenize
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


FALLBACK_STOPWORDS = {
    "a",
    "al",
    "algo",
    "como",
    "con",
    "cual",
    "de",
    "del",
    "el",
    "ella",
    "ellos",
    "en",
    "es",
    "esta",
    "este",
    "hay",
    "la",
    "las",
    "lo",
    "los",
    "me",
    "mi",
    "mis",
    "para",
    "pero",
    "por",
    "que",
    "se",
    "sin",
    "su",
    "sus",
    "te",
    "tu",
    "un",
    "una",
    "uno",
    "y",
    "ya",
}

TOKEN_EQUIVALENTS = {
    "app": "aplicacion",
    "apps": "aplicaciones",
    "banca": "banco",
    "clave": "contrasena",
    "claves": "contrasenas",
    "computer": "ordenador",
    "computadora": "ordenador",
    "correos": "correo",
    "correo": "correo",
    "cpu": "procesador",
    "credencial": "credenciales",
    "crypto": "criptomoneda",
    "cryptomonedas": "criptomoneda",
    "email": "correo",
    "emails": "correo",
    "equipo": "ordenador",
    "fallos": "fallo",
    "hackeado": "comprometido",
    "hackearon": "comprometido",
    "login": "acceso",
    "logins": "acceso",
    "mail": "correo",
    "malicioso": "malware",
    "minando": "mineria",
    "minar": "mineria",
    "movil": "telefono",
    "password": "contrasena",
    "pc": "ordenador",
    "portatil": "ordenador",
    "popups": "popup",
    "ram": "memoria",
    "sms": "mensaje",
    "troyano": "troyano",
    "usb": "usb",
    "virus": "malware",
    "wifi": "wifi",
}


def _prepare_nltk():
    try:
        nltk.data.find("tokenizers/punkt")
    except LookupError:
        try:
            nltk.download("punkt", quiet=True)
        except Exception:
            pass

    try:
        nltk.data.find("corpora/stopwords")
    except LookupError:
        try:
            nltk.download("stopwords", quiet=True)
        except Exception:
            pass


_prepare_nltk()

try:
    STOPWORDS = set(stopwords.words("spanish"))
except LookupError:
    STOPWORDS = FALLBACK_STOPWORDS

STEMMER = SnowballStemmer("spanish")


def clean_text(text):
    text = str(text or "").lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokenize(text):
    clean = clean_text(text)
    if not clean:
        return []

    try:
        return word_tokenize(clean, language="spanish")
    except LookupError:
        return clean.split()


def normalize_token(token):
    canonical = TOKEN_EQUIVALENTS.get(token, token)
    if len(canonical) <= 2:
        return ""
    return STEMMER.stem(canonical)


def remove_stopwords(tokens):
    clean_tokens = []

    for token in tokens:
        if token not in STOPWORDS and len(token) > 2:
            clean_tokens.append(token)

    return clean_tokens


def stem_tokens(tokens):
    stems = []

    for token in tokens:
        normalized = normalize_token(token)
        if normalized:
            stems.append(normalized)

    return stems


def preprocess_text(text):
    tokens = tokenize(text)
    tokens = remove_stopwords(tokens)
    tokens = stem_tokens(tokens)
    return tokens


def preprocess_sentence(text):
    return " ".join(preprocess_text(text))


def _vectorizer_config():
    return {
        "lowercase": False,
        "ngram_range": (1, 2),
        "token_pattern": None,
        "tokenizer": preprocess_text,
    }


def build_count_model(documents):
    vectorizer = CountVectorizer(binary=True, **_vectorizer_config())
    matrix = vectorizer.fit_transform(documents)
    return vectorizer, matrix


def build_tfidf_model(documents):
    vectorizer = TfidfVectorizer(sublinear_tf=True, **_vectorizer_config())
    matrix = vectorizer.fit_transform(documents)
    return vectorizer, matrix


def build_hybrid_vector_model(documents):
    if not documents:
        return {
            "count_vectorizer": None,
            "count_matrix": None,
            "tfidf_vectorizer": None,
            "tfidf_matrix": None,
        }

    count_vectorizer, count_matrix = build_count_model(documents)
    tfidf_vectorizer, tfidf_matrix = build_tfidf_model(documents)
    return {
        "count_vectorizer": count_vectorizer,
        "count_matrix": count_matrix,
        "tfidf_vectorizer": tfidf_vectorizer,
        "tfidf_matrix": tfidf_matrix,
    }


def compute_similarity_scores(text, vectorizer, matrix):
    if vectorizer is None or matrix is None:
        return np.array([])

    text_vector = vectorizer.transform([text])
    return cosine_similarity(text_vector, matrix)[0]


def compute_hybrid_similarity_scores(text, model, tfidf_weight=0.65):
    if not model:
        return np.array([])

    count_scores = compute_similarity_scores(
        text,
        model.get("count_vectorizer"),
        model.get("count_matrix"),
    )
    tfidf_scores = compute_similarity_scores(
        text,
        model.get("tfidf_vectorizer"),
        model.get("tfidf_matrix"),
    )

    if count_scores.size == 0:
        return tfidf_scores
    if tfidf_scores.size == 0:
        return count_scores

    count_weight = 1.0 - tfidf_weight
    return (count_scores * count_weight) + (tfidf_scores * tfidf_weight)


def all_terms_in_text(text, phrase):
    text_tokens = set(preprocess_text(text))
    phrase_tokens = preprocess_text(phrase)

    if not phrase_tokens:
        return False

    return all(token in text_tokens for token in phrase_tokens)


def token_overlap_ratio(text, phrase):
    text_tokens = set(preprocess_text(text))
    phrase_tokens = preprocess_text(phrase)

    if not phrase_tokens:
        return 0.0

    matched = sum(1 for token in phrase_tokens if token in text_tokens)
    return matched / len(phrase_tokens)
