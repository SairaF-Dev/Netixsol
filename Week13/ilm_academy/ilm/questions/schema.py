"""Question format (one source of truth for Day 2 IRT, Day 3 generation, Day 4 grading).

Three types share the same tags:
  concepts    first one = the main concept (must exist in ilm/graph/concepts.yaml)
  difficulty  1-5, the AUTHOR'S GUESS. Day 2 IRT measures the real one; Day 3 compares them.
  bloom       how deep the thinking goes (remember ... create)

The lesson link is NOT stored here: it comes from the concept's taught_in, so moving a
concept to another lesson can never leave questions pointing at the old one.
"""
from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

BLOOM = ("remember", "understand", "apply", "analyze", "evaluate", "create")
Bloom = Literal["remember", "understand", "apply", "analyze", "evaluate", "create"]
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")  # a typo like "anwser:" is an error, not ignored

    id: Annotated[str, StringConstraints(pattern=r"^[a-z0-9_]+-\d{2}$")]
    concepts: list[str] = Field(min_length=1)
    difficulty: int = Field(ge=1, le=5)
    bloom: Bloom
    stem: Text
    code: str | None = None                       # snippet shown with the question
    origin: Literal["authored", "generated"] = "authored"


class MCQ(_Base):
    type: Literal["mcq"]
    options: list[Text] = Field(min_length=3, max_length=5)
    answer: int
    misconceptions: dict[int, Text]               # wrong option index -> the belief behind it
    check_output: bool = False                    # run `code`; its output must be options[answer]

    @model_validator(mode="after")
    def _consistent(self):
        if not 0 <= self.answer < len(self.options):
            raise ValueError(f"answer {self.answer} is not an option index")
        if len(set(self.options)) != len(self.options):
            raise ValueError("duplicate options")
        wrong = set(range(len(self.options))) - {self.answer}
        if set(self.misconceptions) != wrong:
            raise ValueError(f"every wrong option needs a misconception: need {sorted(wrong)}, "
                             f"got {sorted(self.misconceptions)}")
        if self.check_output and not self.code:
            raise ValueError("check_output needs code")
        return self


class Short(_Base):
    type: Literal["short"]
    accept: list[Text] = []      # auto-graded: any of these (after normalising) is correct
    rubric: list[Text] = []      # explain-type: graded against points (LLM/human, Day 4)
    check_output: bool = False   # run `code`; its output must be in accept

    @model_validator(mode="after")
    def _gradable(self):
        if not self.accept and not self.rubric:
            raise ValueError("short answer needs accept (auto-graded) or rubric (explain)")
        if self.check_output and not (self.code and self.accept):
            raise ValueError("check_output needs code and accept")
        return self


class Test(BaseModel):
    """call and expect are Python expressions: expect "'hi'" is the string hi."""
    model_config = ConfigDict(extra="forbid")
    call: Text
    expect: Annotated[str, Field(strict=True)] | None = None
    raises: str | None = None                    # exception class name, e.g. ValueError
    hidden: bool = False                         # Day 4: students see only visible tests

    @model_validator(mode="after")
    def _one_outcome(self):
        if (self.expect is None) == (self.raises is None):
            raise ValueError("a test needs exactly one of expect / raises")
        return self


class Code(_Base):
    type: Literal["code"]
    function: Annotated[str, StringConstraints(pattern=r"^[A-Za-z_]\w*$")]
    starter: str | None = None
    solution: str
    buggy: str | None = None     # a typical wrong solution: the tests MUST catch it
    tests: list[Test] = Field(min_length=2)

    @model_validator(mode="after")
    def _tests_and_level(self):
        if not any(t.hidden for t in self.tests) or all(t.hidden for t in self.tests):
            raise ValueError("needs at least one visible and one hidden test")
        if self.bloom in ("remember", "understand"):
            raise ValueError("writing code is at least 'apply' in Bloom's levels")
        return self


Question = Annotated[Union[MCQ, Short, Code], Field(discriminator="type")]
