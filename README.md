# Commitizen Conventional + JIRA ruleset

These rules for Commitizen extend the regular Conventional Commits rules with:

* Requiring a JIRA issue in the message (optional)
* JIRA issue link added to the messages in the changelog
* Nicer words for the commit types in the changelog

Inspired by and comparable with [cz-github-jira-conventional](https://github.com/apheris/cz-github-jira-conventional).
But without GitHub.

It's different from [conventional_jira](https://github.com/Crystalix007/conventional_jira)
because it doesn't require the JIRA issue ID to be the scope.

## Usage

See <https://commitizen-tools.github.io/commitizen/customization/#2-customize-through-customizing-a-class>.

```shell
pip install cz_conventional_jira
```

```toml
[tool.commitizen]
name = "cz_conventional_jira"
# ...
jira_require = true # Whether to require a JIRA issue ID in the commits. Defaults to false.
jira_url = "https://my.atlassian.net" # Required. Defaults to none.
jira_prefix = "MYPROJ-" # What issue IDs have to start with. E.g. to limit to a specific project. Defaults to none.
```
