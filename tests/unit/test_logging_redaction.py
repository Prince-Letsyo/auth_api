from src.core.logging import filter_sensitive


def test_filter_sensitive_redacts_nested_fields():
    data = {
        "token": "top",
        "nested": {
            "password": "secret",
            "items": [
                {"api_key": "k1"},
                {"otp": "123456"},
                {"safe": "value"},
            ],
        },
        "code": "9999",
    }

    redacted = filter_sensitive(data)

    assert redacted["token"] == "[REDACTED]"
    assert redacted["nested"]["password"] == "***"
    assert redacted["nested"]["items"][0]["api_key"] == "[REDACTED]"
    assert redacted["nested"]["items"][1]["otp"] == "[REDACTED]"
    assert redacted["nested"]["items"][2]["safe"] == "value"
    assert redacted["code"] == "[REDACTED]"
