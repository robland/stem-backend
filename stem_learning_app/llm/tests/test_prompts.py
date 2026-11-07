import pytest

from llm.prompts import PROMPTS, Prompt, latest_prompt

PROMPT = Prompt(name="demo", version=1, system=r"Calcule $\frac{a}{b}$ pour {{ niveau }}.", user="{{niveau}} \\ce{H2O}")


def test_render_substitutes_variables_and_keeps_latex():
    rendered = PROMPT.render(niveau="3e")

    assert rendered.id == "demo.v1"
    assert rendered.system == r"Calcule $\frac{a}{b}$ pour 3e."
    assert rendered.user == "3e \\ce{H2O}"


def test_render_rejects_missing_variable():
    with pytest.raises(ValueError, match="manquantes=\\['niveau'\\]"):
        PROMPT.render()


def test_render_rejects_unknown_variable():
    with pytest.raises(ValueError, match="inconnues=\\['matiere'\\]"):
        PROMPT.render(niveau="3e", matiere="maths")


def test_latest_prompt_picks_highest_version(monkeypatch):
    v2 = Prompt(name="extraction", version=2, system="s", user="u")
    monkeypatch.setitem(PROMPTS, v2.id, v2)

    assert latest_prompt("extraction") is v2


def test_latest_prompt_unknown_name():
    with pytest.raises(KeyError):
        latest_prompt("inexistant")


def test_registered_prompts_are_consistent():
    for prompt_id, prompt in PROMPTS.items():
        assert prompt_id == prompt.id
        assert "<" not in prompt.system, "les prompts ne doivent pas suggérer de HTML"
