import pytest
from sympy import Symbol

from grading.chemistry import FormulaError, balance_report, is_simplest, normalize_formula, parse_formula
from grading.symbolic import ExpressionError, equivalent, parse
from grading.text import close_enough, normalize_text, parse_number
from grading.units import UnitError, convert


class TestText:
    @pytest.mark.parametrize(
        "given, expected",
        [("  Le Sommet. ", "le sommet"), ("l’hypoténuse", "l'hypoténuse"), ("deux   mots", "deux mots")],
    )
    def test_normalize(self, given, expected):
        assert normalize_text(given) == expected

    def test_accents_are_kept(self):
        assert normalize_text("a") != normalize_text("à")

    @pytest.mark.parametrize(
        "given, expected",
        [("2,5", 2.5), ("2 500", 2500), ("-3", -3), ("2,5×10^3", 2500), ("2.5e-3", 0.0025), ("4x10^(-2)", 0.04),
         (7, 7.0), ("−1", -1)],
    )
    def test_parse_number(self, given, expected):
        assert parse_number(given) == pytest.approx(expected)

    @pytest.mark.parametrize("given", ["", "deux", "2,5,3", True, None, "1e"])
    def test_unreadable_number(self, given):
        assert parse_number(given) is None

    def test_close_enough_includes_bounds(self):
        assert close_enough(1.1, 1.0, 0.1)
        assert not close_enough(1.2, 1.0, 0.1)


class TestSymbolic:
    @pytest.mark.parametrize(
        "a, b",
        [("2(x+1)", "2x+2"), ("(x+1)^2", "x^2 + 2x + 1"), ("x^2-4x+3", "(x-1)(x-3)"), ("sqrt(x^2)", "abs(x)"),
         ("1/2 x", "x/2"), ("0,5x", "x/2"), ("2xy", "2*x*y"), ("ln(e^x)", "x"), ("2x − 4", "2*x-4"), ("x²", "x*x")],
    )
    def test_equivalent(self, a, b):
        variables = ["x", "y"]
        assert equivalent(parse(a, variables), parse(b, variables), variables)

    @pytest.mark.parametrize("a, b", [("2x+4", "2x-4"), ("x^2", "2x"), ("sqrt(x)", "x"), ("1/x", "x")])
    def test_not_equivalent(self, a, b):
        assert not equivalent(parse(a, ["x"]), parse(b, ["x"]), ["x"])

    def test_constants(self):
        assert equivalent(parse("2pi", []), parse("pi+pi", []), [])
        assert not equivalent(parse("3", []), parse("pi", []), [])

    @pytest.mark.parametrize(
        "text, message",
        [
            ("", "vide"),
            ("2*z", "variables attendues : x"),
            ("x" * 201, "trop longue"),
            ("2x +", "illisible"),
            ("(x+1", "illisible"),
            ("9^9^9", "Exposant"),
            ("2^1000", "Exposant"),
            ("x; import os", "Caractère"),
            ("__import__('os')", "Caractère"),
            ("x.__class__", "Caractère"),
            ("lambda x", "inconnu"),
            ("open(x)", "inconnu"),
            ("Symbol(x)", "inconnu"),
        ],
    )
    def test_rejected_input(self, text, message):
        with pytest.raises(ExpressionError, match=message):
            parse(text, ["x"])

    def test_undefined_points_are_skipped(self):
        assert equivalent(parse("(x^2-1)/(x-1)", ["x"]), parse("x+1", ["x"]), ["x"])

    def test_parse_returns_sympy_expression(self):
        assert parse("2x", ["x"]).free_symbols == {Symbol("x")}


class TestChemistry:
    @pytest.mark.parametrize(
        "formula, atoms, charge",
        [
            ("H2O", {"H": 2, "O": 1}, 0),
            ("Ca(OH)2", {"Ca": 1, "O": 2, "H": 2}, 0),
            ("Al2(SO4)3", {"Al": 2, "S": 3, "O": 12}, 0),
            ("CuSO4·5H2O", {"Cu": 1, "S": 1, "O": 9, "H": 10}, 0),
            ("H₂O", {"H": 2, "O": 1}, 0),
            ("SO4^{2-}", {"S": 1, "O": 4}, -2),
            ("SO₄²⁻", {"S": 1, "O": 4}, -2),
            ("Fe^3+", {"Fe": 1}, 3),
            ("Na+", {"Na": 1}, 1),
            ("Cl-", {"Cl": 1}, -1),
            ("e-", {}, -1),
        ],
    )
    def test_parse(self, formula, atoms, charge):
        assert parse_formula(formula) == (atoms, charge)

    @pytest.mark.parametrize("formula", ["", "Xx2", "h2o", "Ca(OH", "CaOH)2", "2", "H0"])
    def test_unreadable(self, formula):
        with pytest.raises(FormulaError):
            parse_formula(formula)

    def test_balanced(self):
        assert balance_report(["H2", "O2"], ["H2O"], [2, 1, 2]) == []
        assert balance_report(["Fe", "O2"], ["Fe2O3"], [4, 3, 2]) == []

    def test_unbalanced_names_the_element(self):
        assert balance_report(["H2", "O2"], ["H2O"], [1, 1, 1]) == [
            "Le nombre d'atomes de O n'est pas conservé (2 à gauche, 1 à droite)."
        ]

    def test_charges_must_be_conserved(self):
        assert balance_report(["Fe^{3+}", "e-"], ["Fe^{2+}"], [1, 1, 1]) == []
        issues = balance_report(["Fe^{3+}"], ["Fe^{2+}"], [1, 1])
        assert "charges" in issues[0]

    def test_simplest(self):
        assert is_simplest([2, 1, 2]) and not is_simplest([4, 2, 4])

    def test_normalize(self):
        assert normalize_formula(" H₂ O ") == "H2O"


class TestUnits:
    @pytest.mark.parametrize(
        "value, source, target, expected",
        [
            (2.5, "km", "m", 2500), (90, "km/h", "m/s", 25), (1, "m²", "cm2", 1e4), (1.5, "L", "mL", 1500),
            (1, "dm3", "L", 1), (2, "h", "min", 120), (1, "kWh", "J", 3.6e6), (500, "g", "kg", 0.5),
            (1, "t", "kg", 1000), (1, "g/L", "kg/m3", 1), (2, "mA", "A", 0.002),
        ],
    )
    def test_convert(self, value, source, target, expected):
        assert convert(value, source, target) == pytest.approx(expected)

    @pytest.mark.parametrize("source, target", [("km", "s"), ("°C", "K"), ("m/s/s", "m"), ("", "m")])
    def test_unsupported(self, source, target):
        with pytest.raises(UnitError):
            convert(1, source, target)
