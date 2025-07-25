import re
from posixpath import join as urlpathjoin
from typing import TypedDict
from urllib.parse import urlparse, ParseResult, urlunparse

from commitizen import git
from commitizen.config import BaseConfig
from commitizen.cz.conventional_commits import ConventionalCommitsCz
from commitizen.cz.exceptions import CzException
from commitizen.cz.utils import required_validator
from commitizen.defaults import Settings
from commitizen.question import CzQuestion, InputQuestion

JIRA_ISSUE_REGEX = re.compile(r"\b[A-Z][A-Z0-9_]{1,9}-[1-9][0-9]{1,4}\b")  # https://regex101.com/r/ZEzo2R/10


class NonExportedConventionalCommitsAnswers(TypedDict):
    prefix: str
    scope: str
    subject: str
    body: str
    footer: str
    is_breaking_change: bool


class ConventionalJiraAnswers(NonExportedConventionalCommitsAnswers, total=False):
    jira_issue_ids: str


class ConventionalJiraSettings(Settings, total=False):
    jira_require: bool
    jira_url: str
    jira_prefix: str


class CzConventionalJira(ConventionalCommitsCz):
    def __init__(self, config: BaseConfig):
        super().__init__(config)
        # This is cheating. Settings(TypedDict) does not know and should not hold ConventionalJiraSettings keys.
        # But runtime it's just a dict. I don't feel like overriding the entire CZ's read_cfg().
        settings = ConventionalJiraSettings(**self.config.settings)
        self.jira_require = settings.get("jira_require", False)
        self.jira_url: ParseResult = urlparse(str(settings["jira_url"]))  # required
        self.jira_prefix: str = str(settings.get("jira_prefix", ""))

    # https://github.com/angular/angular/blob/22b96b9/CONTRIBUTING.md#type
    change_type_map = {
        "build": "Build system or dependency changes",
        "ci": "CI config or scripts changes",
        "docs": "Documentation (only) changes",
        "feat": "New features",
        "fix": "Bug fixes",
        "perf": "Performance improvements",
        "refactor": "Refactoring changes",
        "style": "Styling (not affecting code) changes",
        "test": "Added or fixed tests",
    }

    # Preserve any subsequent lines of the commit message
    commit_parser = ConventionalCommitsCz.commit_parser + r"(\n(?P<more_lines>(.|\n)*))?"

    def questions(self) -> list[CzQuestion]:
        conventional_questions = super().questions()
        conventional_questions.append(
            InputQuestion(
                name="jira_issue_ids",
                message="JIRA issue ID(s) separated by space",
                filter=self.filter_jira_issue_ids,
            )
        )
        return conventional_questions

    def message(self, answers: ConventionalJiraAnswers) -> str:
        jira_issue_ids = answers.get("jira_issue_ids", "")
        if jira_issue_ids:
            body = answers.get("body", "")
            answers["body"] = body + ("\n\n" if body else "") + jira_issue_ids
        return super().message(answers)

    def schema(self) -> str:
        schema = super().schema()
        optional = "optional " if not self.jira_require else ""
        schema = schema.replace("<body>", f"<body with {optional}JIRA issue ID(s)>")
        return schema

    def schema_pattern(self) -> str:
        conventional_pattern = super().schema_pattern()  # (?s)(lots|of|types)(\(\S+\))?!?: ([^\n\r]+)((\n\n.*)|(\s*))?$
        if not self.jira_require:
            return conventional_pattern
        pattern = conventional_pattern.removesuffix(r"$")
        pattern += JIRA_ISSUE_REGEX.pattern + r".*"
        return pattern

    def changelog_message_builder_hook(self, parsed: dict, commit: git.GitCommit) -> dict | list | None:
        if super().changelog_message_builder_hook:
            parsed = super().changelog_message_builder_hook(parsed, commit)
        message = parsed["message"]

        message = JIRA_ISSUE_REGEX.sub(self._link_to_jira_issue_id, message)

        more_lines = str(parsed.get("more_lines", "") or "")
        for jira_issue_id in JIRA_ISSUE_REGEX.findall(more_lines):
            message += " " + self._link_to_jira_issue_id(jira_issue_id)

        parsed["message"] = message
        return parsed

    def foo(self, m: re.Match) -> str:
        return self._link_to_jira_issue_id(m.group(0))

    def _link_to_jira_issue_id(self, jira_issue_id: str | re.Match) -> str:
        if type(jira_issue_id) is re.Match:
            jira_issue_id = jira_issue_id.group(0)
        jira_issue_url = urlunparse(
            self.jira_url._replace(path=urlpathjoin(self.jira_url.path, f"browse/{jira_issue_id}"))
        )
        link = f"[{jira_issue_id}]({jira_issue_url})"
        return link

    def filter_jira_issue_ids(self, text: str) -> str:
        if not text:
            return ""

        supposed_issue_ids = [i.strip() for i in text.strip().split(" ")]
        for supposed_issue_id in supposed_issue_ids:
            if not JIRA_ISSUE_REGEX.fullmatch(supposed_issue_id):
                raise InvalidAnswerError(f"JIRA issue '{supposed_issue_id}' is not valid.")
            if not supposed_issue_id.startswith(self.jira_prefix):
                raise InvalidAnswerError(f"JIRA issue '{supposed_issue_id}' does not start with '{self.jira_prefix}'.")

        issue_ids = " ".join(supposed_issue_ids)

        if self.jira_require:
            return required_validator(issue_ids, msg="At least one JIRA issue must be given")
        else:
            return issue_ids


class InvalidAnswerError(CzException): ...
