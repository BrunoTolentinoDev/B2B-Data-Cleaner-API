from app.services.validators import is_valid_cnpj, is_valid_email, normalize_cnpj, normalize_email


def test_normalize_email_strips():
    assert normalize_email("  user@example.com  ") == "user@example.com"


def test_is_valid_email():
    assert is_valid_email("user@example.com") is True
    assert is_valid_email("not-an-email") is False
    assert is_valid_email("") is False


def test_normalize_cnpj_keeps_digits():
    assert normalize_cnpj("11.444.777/0001-61") == "11444777000161"


def test_is_valid_cnpj_known_values():
    # Exemplo com dígitos verificadores válidos.
    assert is_valid_cnpj("11.444.777/0001-61") is True
    assert is_valid_cnpj("00.000.000/0000-00") is False

