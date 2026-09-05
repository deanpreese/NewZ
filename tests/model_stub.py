"""A model that says exactly what a test needs it to say.

Not a mock of the validator — the validator under test is the real one. This
stands in for the far side of the local endpoint, so a test can ask what happens
when the model fabricates a quotation, obeys an injected instruction, or invents
a field, without any of those depending on what a real model happens to do
today.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from newz.model.client import Completion, ModelUnavailable


@dataclass
class StubModel:
    reply: str = "<extraction></extraction>"
    model: str = "qwen/qwen3.6-35b-a3b"
    unavailable: bool = False
    prompts: list[tuple[str, str]] = field(default_factory=list)

    def complete(self, system: str, user: str, max_tokens: int = 2048) -> Completion:
        self.prompts.append((system, user))
        if self.unavailable:
            raise ModelUnavailable("the endpoint did not answer")
        return Completion(text=self.reply, model=self.model)


def extraction(*blocks: str) -> str:
    return "<extraction>\n" + "\n".join(blocks) + "\n</extraction>"


def assertion(kind: str, quote: str, summary: str = "", entities: tuple[str, ...] = ()) -> str:
    names = "".join(f"<entity>{name}</entity>" for name in entities)
    return (
        "<assertion>"
        f"<kind>{kind}</kind>"
        f"<quote>{quote}</quote>"
        f"<summary>{summary}</summary>"
        f"<entities>{names}</entities>"
        "</assertion>"
    )


def claim(kind: str, wording: str, quote: str = "") -> str:
    return (
        "<claim>"
        f"<kind>{kind}</kind>"
        f"<wording>{wording}</wording>"
        f"<quote>{quote}</quote>"
        "</claim>"
    )
