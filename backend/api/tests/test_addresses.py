from pathlib import Path


def test_address_routes_are_owner_scoped_and_bounded():
    source = (Path(__file__).parents[1] / "app" / "routes" / "addresses.py").read_text()
    assert source.count("Depends(current_customer)") == 5
    assert "Saved address limit reached" in source
    assert "Address.customer_id == customer.id" in source


def test_default_address_is_reassigned_after_deletion():
    source = (Path(__file__).parents[1] / "app" / "routes" / "addresses.py").read_text()
    assert '@router.put("/{address_id}/default"' in source
    assert "was_default = address.is_default" in source
    assert "replacement.is_default = True" in source
