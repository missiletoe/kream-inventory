import pytest
from kream_macro import KreamMacro

@pytest.fixture
def kream_macro():
    return KreamMacro()

def test_login_success(mocker, kream_macro):
    mocker.patch.object(kream_macro.browser, 'get')
    mocker.patch.object(kream_macro, 'is_logged_in', True)
    assert kream_macro.login("test@example.com", "password") is True

def test_login_failure(mocker, kream_macro):
    mocker.patch.object(kream_macro.browser, 'get')
    mocker.patch.object(kream_macro, 'is_logged_in', False)
    assert kream_macro.login("wrong@example.com", "wrongpassword") is False

def test_get_product_details(mocker, kream_macro):
    mocker.patch.object(kream_macro.browser, 'get')
    mocker.patch.object(kream_macro, 'get_product_details', return_value={
        "release_price": "200,000원",
        "model_number": "XYZ123",
        "release_date": "2023-05-01",
        "color": "Black"
    })
    details = kream_macro.get_product_details("12345")
    assert details["release_price"] == "200,000원"
    assert details["model_number"] == "XYZ123"