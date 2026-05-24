import re
import unicodedata

import nltk
from nltk.corpus import stopwords
from nltk.stem.snowball import SnowballStemmer
from nltk.tokenize import word_tokenize, wordpunct_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


FALLBACK_STOPWORDS = {
    "a",
    "al",
    "algo",
    "como",
    "con",
    "de",
    "del",
    "el",
    "en",
    "es",
    "esta",
    "este",
    "la",
    "las",
    "lo",
    "los",
    "me",
    "mi",
    "mis",
    "muy",
    "para",
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
    "y",
    "yo",
}


def _ensure_nltk_resource(resource_path, download_name):
    try:
        nltk.data.find(resource_path)
    except LookupError:
        try:
            nltk.download(download_name, quiet=True)
        except Exception:
            pass


_ensure_nltk_resource("corpora/stopwords", "stopwords")
_ensure_nltk_resource("tokenizers/punkt", "punkt")

try:
    STOPWORDS = set(stopwords.words("spanish"))
except LookupError:
    STOPWORDS = FALLBACK_STOPWORDS

STEMMER = SnowballStemmer("spanish")


def normalize_text(text):
    if not text:
        return ""

    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokenize(text):
    normalized = normalize_text(text)
    if not normalized:
        return []

    try:
        return word_tokenize(normalized, language="spanish")
    except LookupError:
        return wordpunct_tokenize(normalized)


def remove_stopwords(tokens):
    return [token for token in tokens if token not in STOPWORDS and len(token) > 2]


def stem_tokens(tokens):
    return [STEMMER.stem(token) for token in tokens]


def preprocess_text(text):
    return stem_tokens(remove_stopwords(tokenize(text)))


def contains_all_terms(tokens, phrase):
    phrase_tokens = preprocess_text(phrase)
    if not phrase_tokens:
        return False

    token_set = set(tokens)
    return set(phrase_tokens).issubset(token_set)


def build_tfidf_vectorizer():
    return TfidfVectorizer(
        tokenizer=preprocess_text,
        lowercase=False,
        token_pattern=None,
        ngram_range=(1, 2),
    )


class ExampleIntentDetector:
    def __init__(self, examples_by_intent):
        self.examples = []
        self.labels = []

        for intent, examples in examples_by_intent.items():
            for example in examples:
                if example:
                    self.examples.append(example)
                    self.labels.append(intent)

        self.vectorizer = build_tfidf_vectorizer()
        self.matrix = None

        if self.examples:
            self.matrix = self.vectorizer.fit_transform(self.examples)

    def __call__(self, user_text):
        if self.matrix is None:
            return None, 0.0

        user_vector = self.vectorizer.transform([user_text])
        scores = cosine_similarity(user_vector, self.matrix)[0]

        if scores.size == 0:
            return None, 0.0

        best_index = int(scores.argmax())
        return self.labels[best_index], float(scores[best_index])
