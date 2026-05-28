import contextlib
import logging
import os
from apify_client import ApifyClient
from src.nlp_utils import compute_tf, full_pipeline

DEFAULT_ACTOR_ID = "klondikeking/stack-overflow-scraper"
DEFAULT_API_BASE = "https://api.apify.com/v2"
DEFAULT_MAX_ITEMS = 5
DEFAULT_MAX_ANSWERS = 3
DEFAULT_TIMEOUT = 20
MAX_TEXT_LEN = 500
MAX_QUERY_TERMS = 5

EXTRA_QUERY_STOPWORDS = {
    "buscar",
    "busca",
    "informacion",
    "info",
    "tema",
    "temas",
    "dime",
    "quiero",
    "saber",
    "explicar",
    "explicacion",
    "definir",
    "definicion",
    "como",
    "poder",
    "puedo",
    "hacer",
    "eliminar",
    "quitar",
    "remover",
    "ayuda",
    "problema",
    "necesitar",
    "necesito",
    "ver",
    "opcion",
    "opciones",
    "pregunta",
    "preguntas",
    "solicitar",
    "solicito",
    "sobre",
}

 # fuente: https://stackoverflow.com/questions/32419510/how-to-suppress-print-output-of-a-python-function/32419558#32419558
def _truncate(text, max_len=MAX_TEXT_LEN):
    text = (text or "").strip()
    if len(text) <= max_len:
        return text
    trimmed = text[:max_len].rsplit(" ", 1)[0]
    return (trimmed or text[:max_len]) + "..."


def _get_text_field(payload, *keys):
    for key in keys:
        value = payload.get(key)
        if value:
            return value
    return ""


def _normalize_search_query(text):
    original = (text or "").strip()
    if not original:
        return ""

    tokens = full_pipeline(original)
    filtered = [t for t in tokens if t not in EXTRA_QUERY_STOPWORDS]
    if not filtered:
        filtered = tokens

    if not filtered:
        return original

    tf = compute_tf(filtered)
    order = {}
    for idx, term in enumerate(filtered):
        if term not in order:
            order[term] = idx

    ranked = sorted(tf.keys(), key=lambda term: (-tf[term], order[term]))
    return " ".join(ranked[:MAX_QUERY_TERMS])

# para evitar los prints
@contextlib.contextmanager
def _suppress_actor_output():
    previous_disable = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    devnull_fd = os.open(os.devnull, os.O_WRONLY)
    stdout_fd = os.dup(1)
    stderr_fd = os.dup(2)
    try:
        os.dup2(devnull_fd, 1)
        os.dup2(devnull_fd, 2)
        yield
    finally:
        os.dup2(stdout_fd, 1)
        os.dup2(stderr_fd, 2)
        os.close(stdout_fd)
        os.close(stderr_fd)
        os.close(devnull_fd)
        logging.disable(previous_disable)

class ApifyStackOverflowClient:
    def __init__(self, actor_id=DEFAULT_ACTOR_ID, api_base=DEFAULT_API_BASE, timeout=DEFAULT_TIMEOUT):
        self.token = os.getenv("APIFY_TOKEN", "").strip()
        self.actor_id = actor_id
        self.api_base = api_base.rstrip("/")
        self.timeout = timeout
        self.client = self._build_client() if self.token else None

    def is_configured(self):
        return bool(self.token) and self.client is not None

    def _build_client(self):
        api_url = self.api_base
        if api_url.endswith("/v2"):
            api_url = api_url[:-3]
        try:
            return ApifyClient(self.token, api_url=api_url)
        except TypeError:
            return ApifyClient(self.token)

    def _get_run_field(self, run, *names):
        if isinstance(run, dict):
            for name in names:
                if name in run:
                    return run[name]

        for name in names:
            if hasattr(run, name):
                return getattr(run, name)

        if hasattr(run, "get"):
            for name in names:
                try:
                    value = run.get(name)
                except Exception:
                    value = None
                if value is not None:
                    return value

        if hasattr(run, "to_dict"):
            data = run.to_dict()
            for name in names:
                if name in data:
                    return data[name]

        return None

    def search_questions(self, query, max_items=DEFAULT_MAX_ITEMS, include_answers=True, max_answers_per_question=DEFAULT_MAX_ANSWERS, tags=None, sort="relevance"):
        if not self.is_configured():
            raise RuntimeError("APIFY_TOKEN no configurado")

        normalized_query = _normalize_search_query(query)

        print("Buscando en Stack Overflow, esto puede tardar un momento...")

        safe_sort = (sort or "relevance").lower()
        if safe_sort not in {"relevance", "creation", "votes", "activity"}:
            safe_sort = "relevance"

        payload = {
            "searchQuery": normalized_query,
            "sort": safe_sort,
            "maxItems": max_items,
            "includeAnswers": include_answers,
            "maxAnswersPerQuestion": max_answers_per_question,
        }
        if tags:
            payload["tags"] = tags

        with _suppress_actor_output():
            run = self.client.actor(self.actor_id).call(run_input=payload)
            dataset_id = self._get_run_field(run, "defaultDatasetId", "default_dataset_id")
            if not dataset_id:
                return []
            items = list(self.client.dataset(dataset_id).iterate_items())

        filtered = []
        for item in items or []:
            answer_count = item.get("answerCount")
            if answer_count is None:
                answer_count = item.get("answer_count")
            if answer_count and answer_count > 0:
                filtered.append(item)

        if len(filtered) > max_items:
            filtered = filtered[:max_items]
        return filtered


def format_question_list(items):
    if not items:
        return (
            "No he encontrado resultados en Stack Overflow. "
            "Prueba con una consulta mas concreta."
        )

    total = len(items)
    lines = [
        "No he encontrado informacion en la base local.",
        "Estas son las preguntas mas parecidas en Stack Overflow:",
        "",
    ]

    for i, item in enumerate(items, 1):
        title = _get_text_field(item, "title") or "(Sin titulo)"
        score = item.get("score")
        answer_count = item.get("answerCount")
        if answer_count is None:
            answer_count = item.get("answer_count")
        tags = item.get("tags") or []

        lines.append(f"{i}) {title}")

        meta = []
        if score is not None:
            meta.append(f"score {score}")
        if answer_count is not None:
            meta.append(f"respuestas {answer_count}")
        if meta:
            lines.append("   " + " | ".join(meta))

        if tags:
            if isinstance(tags, list):
                tag_text = ", ".join(str(tag) for tag in tags[:5])
            else:
                tag_text = str(tags)
            lines.append(f"   tags: {tag_text}")

        if i < total:
            lines.append("")

    lines.append(
        "Escribe el numero para ver respuestas y comentarios, "
        "o escribe 'otra consulta' para buscar otra cosa."
    )
    return "\n".join(lines)


def format_question_details(item):
    title = _get_text_field(item, "title") or "(Sin titulo)"
    score = item.get("score", "?")
    answer_count = item.get("answerCount")
    if answer_count is None:
        answer_count = item.get("answer_count")
    tags = item.get("tags") or []
    body = _truncate(_get_text_field(item, "body"))

    lines = [
        f"Pregunta: {title}",
        f"Puntuacion: {score}",
    ]
    if answer_count is not None:
        lines.append(f"Respuestas: {answer_count}")
    if tags:
        if isinstance(tags, list):
            tag_text = ", ".join(str(tag) for tag in tags[:8])
        else:
            tag_text = str(tags)
        lines.append(f"Tags: {tag_text}")
    if body:
        lines.append("")
        lines.append(body)

    question_comments = item.get("comments", []) or []
    if question_comments:
        lines.append("")
        lines.append("Comentarios de la pregunta:")
        for c in question_comments[:3]:
            c_body = _truncate(_get_text_field(c, "body", "text"))
            if c_body:
                lines.append(f"- {c_body}")

    answers = item.get("answers", []) or []
    if answers:
        lines.append("")
        lines.append("Respuestas destacadas:")
        shown = answers[:DEFAULT_MAX_ANSWERS]
        total_answers = len(shown)
        for i, ans in enumerate(shown, 1):
            ans_score = ans.get("score", "?")
            accepted = " aceptada" if ans.get("isAccepted") else ""
            lines.append(f"{i}) Score {ans_score}{accepted}")
            ans_body = _truncate(_get_text_field(ans, "body"))
            if ans_body:
                lines.append(f"   {ans_body}")

            ans_comments = ans.get("comments", []) or []
            if ans_comments:
                lines.append("   Comentarios:")
                for c in ans_comments[:2]:
                    c_body = _truncate(_get_text_field(c, "body", "text"))
                    if c_body:
                        lines.append(f"   - {c_body}")
            if i < total_answers:
                lines.append("")
    else:
        lines.append("")
        lines.append("No hay respuestas disponibles para esta pregunta.")

    return "\n".join(lines)
