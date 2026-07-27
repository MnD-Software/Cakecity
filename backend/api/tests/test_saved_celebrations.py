from pathlib import Path

from app.models import SavedCake, SavedMessage


def test_saved_celebration_models_are_owner_scoped_and_bounded():
    assert SavedCake.__table__.c.customer_id.foreign_keys
    assert SavedCake.__table__.c.product_id.foreign_keys
    assert SavedMessage.__table__.c.label.type.length == 80
    assert SavedMessage.__table__.c.message.type.length == 160


def test_saved_routes_require_identity_and_apply_collection_limits():
    source = (Path(__file__).parents[1] / "app" / "routes" / "saved.py").read_text()
    assert source.count("Depends(current_customer)") == 6
    assert ">= 100" in source
    assert ">= 30" in source
    assert 'Product.status == "publish"' in source
