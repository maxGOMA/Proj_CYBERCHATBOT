import re
import math
import nltk
import spacy
from nltk.corpus import stopwords

nltk.download("stopwords", quiet=True)

# cargo la libreria en su version en español:
try:
    nlp = spacy.load("es_core_news_sm")
except OSError:
    raise OSError("Ejecuta: python -m spacy download es_core_news_sm")

STOPWORDS = set(stopwords.words("spanish"))


def clean_text(text):
    text = text.lower()
    for src, dst in {"á":"a","à":"a","é":"e","è":"e","í":"i","ì":"i",
                     "ó":"o","ò":"o","ú":"u","ù":"u","ü":"u","ñ":"n"}.items():
        text = text.replace(src, dst)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokenize(text):
    tokens = clean_text(text).split()
    return [t for t in tokens if t not in STOPWORDS and len(t) > 2]


def lemmatize(tokens):
    doc = nlp(" ".join(tokens))
    return [t.lemma_ for t in doc if not t.is_stop and len(t.lemma_) > 2]


def full_pipeline(text):
    return lemmatize(tokenize(text))


def compute_tf(tokens):
    total = len(tokens)
    if total == 0:
        total = 1

    tf = {}
    for t in tokens:
        if t in tf:
            tf[t] = tf[t] + 1
        else:
            tf[t] = 1

    tf_norm = {}
    for t in tf:
        tf_norm[t] = tf[t] / float(total)

    return tf_norm


def compute_idf(corpus):
    N = len(corpus)
    idf = {}

    for doc in corpus:
        unique_terms = set(doc)
        for t in unique_terms:
            if t in idf:
                idf[t] = idf[t] + 1
            else:
                idf[t] = 1

    idf_result = {}
    for t in idf:
        df = idf[t]
        idf_result[t] = math.log(N / float(1 + df))

    return idf_result


def tfidf_vector(tokens, idf):
    tf = compute_tf(tokens)

    vec = {}
    for t in tf:
        if t in idf:
            vec[t] = tf[t] * idf[t]
        else:
            vec[t] = tf[t] * 0

    return vec


def cosine_similarity(v1, v2):
    # dot product
    dot = 0.0
    for t in v1:
        v1_val = v1[t]
        v2_val = v2.get(t, 0)
        dot = dot + (v1_val * v2_val)

    # norm1
    sum_sq1 = 0.0
    for x in v1.values():
        sum_sq1 = sum_sq1 + (x * x)
    norm1 = math.sqrt(sum_sq1)

    # norm2
    sum_sq2 = 0.0
    for x in v2.values():
        sum_sq2 = sum_sq2 + (x * x)
    norm2 = math.sqrt(sum_sq2)

    if norm1 != 0 and norm2 != 0:
        return dot / (norm1 * norm2)
    else:
        return 0.0


def detect_intent(user_text, intents_corpus, idf):
    user_vec = tfidf_vector(full_pipeline(user_text), idf)

    best = None
    best_score = -1.0

    for intent_name, lemmas in intents_corpus.items():
        intent_vec = tfidf_vector(lemmas, idf)
        score = cosine_similarity(user_vec, intent_vec)

        if score > best_score:
            best_score = score
            best = intent_name

    return best, best_score
