import re
import unicodedata


def remove_accents(text):
    normalized = unicodedata.normalize("NFD", text)
    cleaned = ""

    for char in normalized:
        if unicodedata.category(char) != "Mn":
            cleaned = cleaned + char

    return cleaned


def clean_text(text):
    if text is None:
        return ""

    text = str(text)
    text = text.lower()
    text = remove_accents(text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    text = text.strip()
    return text


def tokenize(text):
    clean = clean_text(text)

    if clean == "":
        return []

    parts = clean.split(" ")
    tokens = []

    for part in parts:
        if part != "":
            tokens.append(part)

    return tokens


def count_common_words(text1, text2):
    tokens1 = tokenize(text1)
    tokens2 = tokenize(text2)
    count = 0

    for token in tokens1:
        if token in tokens2:
            count = count + 1

    return count


def text_contains_term(text, term):
    clean_text_value = clean_text(text)
    clean_term = clean_text(term)

    if clean_term == "":
        return False

    if " " in clean_term:
        if clean_term in clean_text_value:
            return True
        else:
            return False
    else:
        tokens = tokenize(clean_text_value)

        if clean_term in tokens:
            return True
        else:
            return False