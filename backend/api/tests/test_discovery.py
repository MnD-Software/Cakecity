from decimal import Decimal
from types import SimpleNamespace

from app.services.discovery import parse_intent, rank_products


def product(name: str, price: str, text: str, rating: str = "4.7"):
    return SimpleNamespace(
        name=name, price_kes=Decimal(price), description=text, short_description="",
        categories=["Birthday Cakes"], attributes=[], average_rating=Decimal(rating),
        review_count=100, in_stock=True, status="publish",
    )


def test_extracts_human_occasion_budget_and_recipient_intent():
    intent = parse_intent("I need a chocolate birthday cake for a 6 year old girl under KES 4,000")
    assert intent.occasion == "birthday"
    assert intent.flavour == "chocolate"
    assert intent.recipient == "child"
    assert intent.age == 6
    assert intent.budget_kes == Decimal("4000")


def test_explainable_ranking_prefers_matching_in_budget_product():
    intent = parse_intent("elegant chocolate birthday cake under 4000")
    ranked = rank_products([
        product("Midnight Chocolate", "3400", "Elegant dark cocoa ganache"),
        product("Vanilla Wedding", "5200", "Vanilla cream"),
    ], intent, 2)
    assert ranked[0][2].name == "Midnight Chocolate"
    assert "Within your budget" in ranked[0][1]
    assert any("Chocolate" in reason for reason in ranked[0][1])
