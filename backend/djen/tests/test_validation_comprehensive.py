"""
Comprehensive tests for djen.api.validation module.

Tests CNJ, OAB, and Tribunal validators with edge cases.
"""

import pytest
from djen.api.validation import (
    CNJValidator,
    OABValidator,
    TribunalValidator,
    ValidationResult,
    validate_cnj,
    validate_oab,
    validate_tribunal,
    get_tribunais,
    TRIBUNAIS_CNJ,
)


# =========================================================================
# ValidationResult model
# =========================================================================

class TestValidationResult:
    def test_valid_result(self):
        r = ValidationResult(valid=True, field="test", value="v")
        assert r.valid is True
        assert r.message is None

    def test_invalid_result(self):
        r = ValidationResult(valid=False, field="test", message="err")
        assert r.valid is False
        assert r.message == "err"

    def test_to_dict(self):
        r = ValidationResult(valid=True, field="f", message="m", value="v")
        d = r.to_dict()
        assert d == {"valid": True, "field": "f", "message": "m", "value": "v"}

    def test_to_dict_none_values(self):
        r = ValidationResult(valid=False, field="f")
        d = r.to_dict()
        assert d["message"] is None
        assert d["value"] is None


# =========================================================================
# CNJ Validator
# =========================================================================

class TestCNJValidator:
    def test_valid_full_format(self):
        r = CNJValidator.validate("0000832-56.2018.8.10.0001")
        assert r.valid is True

    def test_valid_full_format_2(self):
        r = CNJValidator.validate("1234567-89.2024.5.02.0001")
        assert r.valid is True

    def test_valid_20_digits_no_punctuation(self):
        r = CNJValidator.validate("00008325620188100001")
        assert r.valid is True
        assert "-" in r.value  # Should be formatted

    def test_empty_string(self):
        r = CNJValidator.validate("")
        assert r.valid is False

    def test_none_like_empty(self):
        r = CNJValidator.validate("")
        assert r.valid is False
        assert "obrigatório" in r.message

    def test_too_short(self):
        r = CNJValidator.validate("12345")
        assert r.valid is False

    def test_too_long(self):
        r = CNJValidator.validate("0000832-56.2018.8.10.00011111")
        assert r.valid is False

    def test_letters_in_number(self):
        r = CNJValidator.validate("ABCDEFG-56.2018.8.10.0001")
        assert r.valid is False

    def test_whitespace_trimmed(self):
        r = CNJValidator.validate("  0000832-56.2018.8.10.0001  ")
        assert r.valid is True

    def test_partial_format(self):
        r = CNJValidator.validate("0000832-56.2018")
        assert r.valid is False

    def test_wrong_separator_still_parses_digits(self):
        """The validator strips non-digits and reformats if 20 digits found."""
        r = CNJValidator.validate("0000832/56.2018.8.10.0001")
        # Has 20 digits after stripping, so validator reformats it
        assert r.valid is True

    def test_validate_cnj_shortcut(self):
        r = validate_cnj("0000832-56.2018.8.10.0001")
        assert r.valid is True

    def test_validate_cnj_shortcut_invalid(self):
        r = validate_cnj("invalid")
        assert r.valid is False


# =========================================================================
# OAB Validator
# =========================================================================

class TestOABValidator:
    def test_valid_oab_with_letter(self):
        r = OABValidator.validate("SP123456A")
        assert r.valid is True

    def test_valid_oab_without_letter(self):
        r = OABValidator.validate("SP123456")
        assert r.valid is True

    def test_valid_oab_7_digits(self):
        r = OABValidator.validate("SP1234567")
        assert r.valid is True

    def test_valid_oab_3_digits(self):
        r = OABValidator.validate("SP123")
        assert r.valid is True

    def test_lowercase_converted_to_upper(self):
        r = OABValidator.validate("sp123456")
        assert r.valid is True
        assert r.value == "SP123456"

    def test_empty_string(self):
        r = OABValidator.validate("")
        assert r.valid is False
        assert "obrigatório" in r.message

    def test_invalid_uf(self):
        r = OABValidator.validate("XX123456")
        assert r.valid is False
        assert "UF" in r.message

    def test_numbers_only_with_uf(self):
        r = OABValidator.validate("123456", uf="SP")
        assert r.valid is True
        assert r.value == "SP123456"

    def test_numbers_only_without_uf(self):
        r = OABValidator.validate("123456")
        assert r.valid is False
        assert "UF" in r.message

    def test_all_valid_ufs(self):
        for uf in OABValidator.VALID_UFS:
            r = OABValidator.validate(f"{uf}123456")
            assert r.valid is True, f"UF {uf} should be valid"

    def test_whitespace_trimmed(self):
        r = OABValidator.validate("  SP123456  ")
        assert r.valid is True

    def test_too_short_number(self):
        r = OABValidator.validate("12")
        assert r.valid is False

    def test_validate_oab_shortcut(self):
        r = validate_oab("SP123456")
        assert r.valid is True

    def test_validate_oab_shortcut_with_uf(self):
        r = validate_oab("123456", uf="RJ")
        assert r.valid is True


# =========================================================================
# Tribunal Validator
# =========================================================================

class TestTribunalValidator:
    def test_valid_tribunal_tjsp(self):
        r = TribunalValidator.validate("tjsp")
        assert r.valid is True
        assert "São Paulo" in r.message

    def test_valid_tribunal_uppercase(self):
        r = TribunalValidator.validate("TJSP")
        assert r.valid is True

    def test_valid_tribunal_mixed_case(self):
        r = TribunalValidator.validate("TjSp")
        assert r.valid is True

    def test_valid_tribunal_stf(self):
        r = TribunalValidator.validate("stf")
        assert r.valid is True

    def test_valid_tribunal_stj(self):
        r = TribunalValidator.validate("stj")
        assert r.valid is True

    def test_valid_tribunal_trt(self):
        r = TribunalValidator.validate("trt1")
        assert r.valid is True

    def test_valid_tribunal_trf(self):
        r = TribunalValidator.validate("trf1")
        assert r.valid is True

    def test_empty_string(self):
        r = TribunalValidator.validate("")
        assert r.valid is False
        assert "obrigatório" in r.message

    def test_invalid_tribunal(self):
        r = TribunalValidator.validate("xyz")
        assert r.valid is False
        assert "não encontrado" in r.message

    def test_invalid_with_suggestions(self):
        r = TribunalValidator.validate("tjs")
        assert r.valid is False
        # Should suggest tjsp, etc.

    def test_whitespace_trimmed(self):
        r = TribunalValidator.validate("  tjsp  ")
        assert r.valid is True

    def test_validate_tribunal_shortcut(self):
        r = validate_tribunal("tjrj")
        assert r.valid is True

    def test_all_tribunais_valid(self):
        for sigla in TRIBUNAIS_CNJ.keys():
            r = TribunalValidator.validate(sigla)
            assert r.valid is True, f"Tribunal {sigla} should be valid"


# =========================================================================
# get_tribunais function
# =========================================================================

class TestGetTribunais:
    def test_get_all_tribunais(self):
        tribunais = get_tribunais()
        assert len(tribunais) > 0
        assert len(tribunais) == len(TRIBUNAIS_CNJ)

    def test_get_tribunais_by_tipo_estadual(self):
        tribunais = get_tribunais(tipo="estadual")
        assert len(tribunais) > 0
        for t in tribunais:
            assert TRIBUNAIS_CNJ[t["sigla"]]["tipo"] == "estadual"

    def test_get_tribunais_by_tipo_federal(self):
        tribunais = get_tribunais(tipo="federal")
        assert len(tribunais) > 0
        for t in tribunais:
            assert TRIBUNAIS_CNJ[t["sigla"]]["tipo"] == "federal"

    def test_get_tribunais_by_tipo_trabalho(self):
        tribunais = get_tribunais(tipo="trabalho")
        assert len(tribunais) > 0

    def test_get_tribunais_by_tipo_superior(self):
        tribunais = get_tribunais(tipo="superior")
        assert len(tribunais) > 0

    def test_get_tribunais_invalid_tipo(self):
        tribunais = get_tribunais(tipo="nonexistent")
        assert len(tribunais) == 0

    def test_tribunais_have_required_fields(self):
        tribunais = get_tribunais()
        for t in tribunais:
            assert "sigla" in t
            assert "nome" in t
