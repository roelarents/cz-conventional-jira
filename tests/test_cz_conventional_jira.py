import re

import pytest
from commitizen.config import BaseConfig
from commitizen.git import GitCommit

from src.cz_conventional_jira.cz_conventional_jira import (
    CzConventionalJira,
    ConventionalJiraAnswers,
    ConventionalJiraSettings,
)

TEST_JIRA_URL = "https://example.com/"


def create_config(update_settings: ConventionalJiraSettings) -> BaseConfig:
    _config = BaseConfig()
    _config.settings.update(
        {
            "jira_url": TEST_JIRA_URL,
        }
    )
    _config.settings.update(update_settings)
    return _config


def create_cz_conventional_jira(update_settings: ConventionalJiraSettings) -> CzConventionalJira:
    return CzConventionalJira(create_config(update_settings))


@pytest.mark.parametrize(
    ["update_settings", "update_answers", "expected"],
    [
        (
            ConventionalJiraSettings(),
            ConventionalJiraAnswers(),
            "prefix(scope): sub\n\nbody\n\nfooter",
        ),
        (
            ConventionalJiraSettings(),
            ConventionalJiraAnswers(jira_issue_ids=""),
            "prefix(scope): sub\n\nbody\n\nfooter",
        ),
        (
            ConventionalJiraSettings(),
            ConventionalJiraAnswers(jira_issue_ids="ABC-123"),
            "prefix(scope): sub\n\nbody\n\nABC-123\n\nfooter",
        ),
        (
            ConventionalJiraSettings(),
            ConventionalJiraAnswers(jira_issue_ids="ABC-123 DEF-456"),
            "prefix(scope): sub\n\nbody\n\nABC-123 DEF-456\n\nfooter",
        ),
    ],
)
def test_message(update_settings: ConventionalJiraSettings, update_answers: ConventionalJiraAnswers, expected: str):
    cz_conventional_jira = create_cz_conventional_jira(update_settings)
    answers = ConventionalJiraAnswers(
        prefix="prefix",
        scope="scope",
        subject="sub",
        body="body",
        footer="footer",
        is_breaking_change=False,
    )
    answers.update(update_answers)
    message = cz_conventional_jira.message(answers)
    assert message == expected


@pytest.mark.parametrize(
    ["update_settings", "parsed", "expected"],
    [
        (
            ConventionalJiraSettings(),
            {"message": "fix: something", "more_lines": ""},
            {
                "message": "fix: something",
            },
        ),
        (
            ConventionalJiraSettings(),
            {"message": "fix: something", "more_lines": "ABC-123"},
            {
                "message": "fix: something [ABC-123](https://example.com/browse/ABC-123)",
            },
        ),
        (
            ConventionalJiraSettings(),
            {"message": "fix: something for ABC-123 and DEF-456 now!"},
            {
                "message": "fix: something for [ABC-123](https://example.com/browse/ABC-123) and [DEF-456](https://example.com/browse/DEF-456) now!",
            },
        ),
        (
            ConventionalJiraSettings(jira_url="https://example.com/subdir"),
            {"message": "fix: something", "more_lines": "ABC-123"},
            {
                "message": "fix: something [ABC-123](https://example.com/subdir/browse/ABC-123)",
            },
        ),
        (
            ConventionalJiraSettings(),
            {"message": "fix: something", "more_lines": "wow, ABC-123 was so difficult.\nalso fixed DEF-456 partially"},
            {
                "message": "fix: something [ABC-123](https://example.com/browse/ABC-123) [DEF-456](https://example.com/browse/DEF-456)",
            },
        ),
    ],
)
def test_changelog_message_builder_hook(update_settings: ConventionalJiraSettings, parsed: dict, expected: dict):
    cz_conventional_jira = create_cz_conventional_jira(update_settings)
    result = cz_conventional_jira.changelog_message_builder_hook(parsed, GitCommit(rev="1234", title="untitled"))
    assert result.get("more_lines") == parsed.get("more_lines")
    assert result.get("message") == expected.get("message")


@pytest.mark.parametrize(
    ["update_settings", "message", "expected"],
    [
        (
            ConventionalJiraSettings(),
            "fix: something",
            True,
        ),
        (
            ConventionalJiraSettings(jira_require=False),
            "fix: something\n\nbla\nbla",
            True,
        ),
        (
            ConventionalJiraSettings(jira_require=True),
            "fix: something",
            False,
        ),
        (
            ConventionalJiraSettings(jira_require=True),
            "fix: something for ABC-123 now!",
            True,
        ),
        (
            ConventionalJiraSettings(jira_require=True),
            "fix: something\nABC-123",
            True,
        ),
        (
            ConventionalJiraSettings(jira_require=True),
            "fix: something\n\nABC-123\nBREAKING_CHANGE",
            True,
        ),
    ],
)
def test_schema_pattern(update_settings: ConventionalJiraSettings, message: str, expected: bool):
    cz_conventional_jira = create_cz_conventional_jira(update_settings)
    pattern = cz_conventional_jira.schema_pattern()
    validator = re.compile(pattern)
    assert bool(validator.match(message)) == expected
