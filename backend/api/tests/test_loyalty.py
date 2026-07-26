from datetime import date
from decimal import Decimal
from app.services.loyalty import tier_for
from app.services.reminders import anniversary_in_year


def test_membership_tiers_follow_lifetime_spend():
    assert tier_for(Decimal("0")) == "silver"
    assert tier_for(Decimal("25000")) == "gold"
    assert tier_for(Decimal("75000")) == "diamond"
    assert tier_for(Decimal("150000")) == "platinum"


def test_leap_day_moment_is_safely_observed_in_non_leap_year():
    assert anniversary_in_year(date(2024, 2, 29), 2027) == date(2027, 2, 28)
    assert anniversary_in_year(date(2024, 2, 29), 2028) == date(2028, 2, 29)
