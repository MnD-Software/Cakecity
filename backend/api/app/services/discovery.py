import re
from dataclasses import dataclass, field
from decimal import Decimal


OCCASIONS = {
    "birthday": {"birthday", "turning", "years old", "year old"},
    "wedding": {"wedding", "bride", "groom", "engagement"},
    "anniversary": {"anniversary", "years together"},
    "corporate": {"corporate", "office", "team", "client", "company"},
    "graduation": {"graduation", "graduate", "graduating"},
    "baby shower": {"baby shower", "new baby", "gender reveal"},
}
FLAVOURS = {
    "chocolate": {"chocolate", "cocoa", "ganache"},
    "vanilla": {"vanilla", "vanilla bean"},
    "caramel": {"caramel", "toffee"},
    "fruit": {"fruit", "berry", "berries", "strawberry", "lemon"},
    "red velvet": {"red velvet", "velvet"},
}
STYLES = {
    "elegant": {"elegant", "luxury", "premium", "classy"},
    "playful": {"fun", "playful", "colourful", "colorful", "cartoon"},
    "romantic": {"romantic", "flowers", "floral", "rose"},
    "minimal": {"minimal", "simple", "clean"},
}
STOP_WORDS = {
    "a", "an", "and", "cake", "cakes", "for", "i", "me", "my", "need", "of", "please",
    "the", "to", "want", "with",
}


@dataclass
class SearchIntent:
    query: str
    occasion: str | None = None
    flavour: str | None = None
    style: str | None = None
    recipient: str | None = None
    age: int | None = None
    budget_kes: Decimal | None = None
    servings: int | None = None
    terms: list[str] = field(default_factory=list)

    def public(self) -> dict:
        return {
            "occasion": self.occasion, "flavour": self.flavour, "style": self.style,
            "recipient": self.recipient, "age": self.age,
            "budget_kes": str(self.budget_kes) if self.budget_kes is not None else None,
            "servings": self.servings, "terms": self.terms,
        }


def _match_group(query: str, groups: dict[str, set[str]]) -> str | None:
    return next((name for name, signals in groups.items() if any(signal in query for signal in signals)), None)


def parse_intent(raw_query: str) -> SearchIntent:
    query = " ".join(raw_query.lower().strip().split())[:240]
    age_match = re.search(r"\b(?:for\s+)?(?:a\s+)?(\d{1,3})\s*(?:year|yr)s?\s*old\b", query)
    serving_match = re.search(r"\b(?:serve|serves|serving|people|guests?)\s*(\d{1,3})\b", query)
    budget_match = re.search(
        r"(?:under|below|within|max(?:imum)?|budget(?:\s+of)?|kes|ksh)\s*[:\-]?\s*(\d[\d,]{2,})",
        query,
    )
    age = int(age_match.group(1)) if age_match else None
    recipient = None
    if age is not None and age <= 12:
        recipient = "child"
    elif any(term in query for term in ("girl", "daughter", "sister", "mum", "mom", "wife", "her")):
        recipient = "her"
    elif any(term in query for term in ("boy", "son", "brother", "dad", "husband", "him")):
        recipient = "him"
    terms = [
        token for token in re.findall(r"[a-z0-9]+", query)
        if len(token) > 2 and token not in STOP_WORDS and not token.isdigit()
    ]
    return SearchIntent(
        query=query,
        occasion=_match_group(query, OCCASIONS),
        flavour=_match_group(query, FLAVOURS),
        style=_match_group(query, STYLES),
        recipient=recipient,
        age=age,
        budget_kes=Decimal(budget_match.group(1).replace(",", "")) if budget_match else None,
        servings=int(serving_match.group(1)) if serving_match else None,
        terms=list(dict.fromkeys(terms))[:16],
    )


def searchable_text(product) -> str:
    attributes = " ".join(
        f"{item.get('name', '')} {' '.join(str(option) for option in item.get('options', []))}"
        for item in (product.attributes or [])
    )
    return " ".join([
        product.name, product.description or "", product.short_description or "",
        " ".join(product.categories or []), attributes,
    ]).lower()


def rank_product(product, intent: SearchIntent, preference_terms: set[str] | None = None) -> tuple[float, list[str]]:
    text = searchable_text(product)
    score = float(product.average_rating or 0) * 0.35 + min(product.review_count or 0, 300) / 300
    reasons: list[str] = []
    matched_terms = [term for term in intent.terms if term in text]
    score += len(matched_terms) * 2.3
    if matched_terms:
        reasons.append(f"Matches {', '.join(matched_terms[:3])}")
    for label, value in (
        ("occasion", intent.occasion), ("flavour", intent.flavour), ("style", intent.style),
    ):
        if value and value in text:
            score += 5
            reasons.append(f"Fits your {value} {label}" if label != "flavour" else f"{value.title()} flavour")
    price = Decimal(product.price_kes)
    if intent.budget_kes is not None:
        if price <= intent.budget_kes:
            score += 4
            reasons.append("Within your budget")
        else:
            score -= min(12, float((price - intent.budget_kes) / Decimal("500")))
    if preference_terms:
        affinity = [term for term in preference_terms if term in text]
        score += len(affinity) * 1.6
        if affinity:
            reasons.append("Inspired by your Cake City history")
    if not reasons:
        reasons.append("Highly rated by Cake City customers")
    return score, reasons[:5]


def rank_products(products: list, intent: SearchIntent, limit: int, preference_terms: set[str] | None = None):
    ranked = [
        (*rank_product(product, intent, preference_terms), product)
        for product in products if product.in_stock and product.status == "publish"
    ]
    ranked.sort(key=lambda item: (-item[0], item[2].name))
    return ranked[:limit]
