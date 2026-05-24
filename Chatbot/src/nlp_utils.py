import re
import unicodedata

import nltk
from nltk.corpus import stopwords
from nltk.stem.snowball import SnowballStemmer
from nltk.tokenize import word_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


FALLBACK_STOPWORDS = {
    "a",
    "al",
    "como",
    "con",
    "de",
    "del",
    "el",
    "en",
    "es",
    "esta",
    "la",
    "las",
    "lo",
    "los",
    "me",
    "mi",
    "para",
    "por",
    "que",
    "se",
    "sin",
    "su",
    "te",
    "tu",
    "un",
    "una",
    "y",
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
    text = text.lower()
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


def remove_stopwords(tokens):
    clean_tokens = []

    for token in tokens:
        if token not in STOPWORDS and len(token) > 2:
            clean_tokens.append(token)

    return clean_tokens


def stem_tokens(tokens):
    stems = []

    for token in tokens:
        stems.append(STEMMER.stem(token))

    return stems


def preprocess_text(text):
    tokens = tokenize(text)
    tokens = remove_stopwords(tokens)
    tokens = stem_tokens(tokens)
    return tokens


def preprocess_sentence(text):
    return " ".join(preprocess_text(text))


def build_tfidf_model(documents):
    vectorizer = TfidfVectorizer()
    matrix = vectorizer.fit_transform(documents)
    return vectorizer, matrix


def compute_similarity_scores(text, vectorizer, matrix):
    processed_text = preprocess_sentence(text)
    text_vector = vectorizer.transform([processed_text])
    scores = cosine_similarity(text_vector, matrix)[0]
    return scores


def all_terms_in_text(text, phrase):
    text_tokens = preprocess_text(text)
    phrase_tokens = preprocess_text(phrase)

    if not phrase_tokens:
        return False

    for token in phrase_tokens:
        if token not in text_tokens:
            return False

    return True
