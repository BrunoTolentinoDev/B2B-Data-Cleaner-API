import re


_EMAIL_RE = re.compile(
    r"^[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Z0-9-]+(\.[A-Z0-9-]+)*\.[A-Z]{2,}$",
    re.IGNORECASE,
)


def normalize_email(email: str) -> str:
    return email.strip()


def is_valid_email(email: str) -> bool:
    if not email:
        return False
    return bool(_EMAIL_RE.match(email))


def normalize_cnpj(cnpj: str) -> str:
    return re.sub(r"[^0-9]", "", (cnpj or "").strip())


def _validate_cnpj_fallback(cnpj_digits: str) -> bool:
    # Algoritmo clássico de validação de CNPJ (dígitos verificadores).
    if len(cnpj_digits) != 14 or not cnpj_digits.isdigit():
        return False

    if cnpj_digits == cnpj_digits[0] * 14:
        return False

    digits = [int(ch) for ch in cnpj_digits]
    weights_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    weights_2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

    sum_1 = sum(digits[i] * weights_1[i] for i in range(12))
    mod_1 = sum_1 % 11
    check_1 = 0 if mod_1 < 2 else 11 - mod_1

    sum_2 = sum(digits[i] * weights_2[i] for i in range(13))
    mod_2 = sum_2 % 11
    check_2 = 0 if mod_2 < 2 else 11 - mod_2

    return digits[12] == check_1 and digits[13] == check_2


def is_valid_cnpj(cnpj: str) -> bool:
    cnpj_digits = normalize_cnpj(cnpj)
    if len(cnpj_digits) != 14:
        return False

    try:
        # Dependência alternativa (similar ao `python-cnpj`) para validação.
        from pycpfcnpj import cpfcnpj

        return bool(cpfcnpj.validate(cnpj_digits))
    except Exception:
        # Se a lib não estiver disponível/compatível, usa validação local.
        return _validate_cnpj_fallback(cnpj_digits)

