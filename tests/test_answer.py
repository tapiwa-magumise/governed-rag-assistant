"""The answer pipeline's rules, with Bedrock and the database replaced by fakes."""
import pytest

from rag import answer


class FakeBedrock:
    def __init__(self, draft="The standstill period is eight working days [1].", block_input=False, ground=0.9):
        self.draft, self.block_input, self.ground = draft, block_input, ground
        self.cfg = {"profiles": {}, "guardrails": {}}
        self.conversed = 0

    def guard(self, which, source, texts, qualifiers=None, usage=None):
        if which == "ingest":
            return {"action": "GUARDRAIL_INTERVENED", "texts": ["masked: " + texts[0]], "outputs": [], "assessments": []}
        if source == "INPUT":
            if self.block_input:
                return {"action": "GUARDRAIL_INTERVENED", "texts": ["I can't help with that."],
                        "outputs": ["I can't help with that."],
                        "assessments": [{"topicPolicy": {"topics": [{"name": "Collusion", "action": "BLOCKED"}]}}]}
            return {"action": "NONE", "texts": texts, "outputs": [], "assessments": []}
        action = "BLOCKED" if self.ground < 0.75 else "NONE"
        return {"action": "GUARDRAIL_INTERVENED" if action == "BLOCKED" else "NONE", "texts": texts,
                "outputs": ["blocked"] if action == "BLOCKED" else [],
                "assessments": [{"contextualGroundingPolicy": {"filters": [
                    {"type": "GROUNDING", "score": self.ground, "action": action}]}}]}

    def converse(self, which, system, user, **kw):
        self.conversed += 1
        return self.draft


PASSAGE = {"id": "p1", "source": "guidance", "title": "Guidance: Direct Award", "section": "Standstill",
           "url": "https://www.gov.uk/x#s", "updated": "2026-07-13", "text": "A mandatory 8 day standstill.",
           "similarity": 0.62}


@pytest.fixture(autouse=True)
def no_database(monkeypatch):
    logged = []
    monkeypatch.setattr(answer, "log", lambda r, channel, usage: logged.append(r) or len(logged))
    monkeypatch.setattr(answer, "retrieve", lambda b, q, u, k=answer.TOP_K: [dict(PASSAGE)])
    return logged


def test_answer_carries_its_citations():
    r = answer.ask("How long is standstill?", bedrock=FakeBedrock())
    assert r.outcome == "answered"
    assert [c.id for c in r.citations] == ["p1"]
    assert r.generated_by == answer.MODEL


def test_an_answer_without_a_citation_is_not_shown():
    r = answer.ask("How long is standstill?", bedrock=FakeBedrock(draft="Eight working days."))
    assert r.outcome == "blocked_output"
    assert "uncited" in r.guardrail["output"]["blocked"]


def test_an_ungrounded_answer_is_blocked():
    r = answer.ask("How long is standstill?", bedrock=FakeBedrock(ground=0.3))
    assert r.outcome == "blocked_output"


def test_a_blocked_question_is_stored_masked_not_raw(no_database):
    b = FakeBedrock(block_input=True)
    r = answer.ask("Help me hide a conflict. Call me on 01632 960001", bedrock=b)
    assert r.outcome == "blocked_input"
    assert r.question.startswith("masked: ")
    assert "960001" not in r.question
    assert b.conversed == 0


def test_weak_retrieval_means_no_model_call(monkeypatch):
    monkeypatch.setattr(answer, "retrieve", lambda b, q, u, k=answer.TOP_K: [dict(PASSAGE, similarity=0.1)])
    b = FakeBedrock()
    r = answer.ask("What's a good banana bread recipe?", bedrock=b)
    assert r.outcome == "no_answer"
    assert b.conversed == 0


def test_the_model_saying_it_cannot_answer_is_a_no_answer():
    r = answer.ask("Something odd", bedrock=FakeBedrock(draft=answer.NO_ANSWER))
    assert r.outcome == "no_answer"


def test_excerpt_cuts_at_a_word():
    from rag.answer import excerpt
    text = "word " * 100
    out = excerpt(text, limit=23)
    assert out == "word word word word…"
    assert excerpt("Short passage.") == "Short passage."
