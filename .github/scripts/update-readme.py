#!/usr/bin/env python3
import copy
import json
import re
from dataclasses import dataclass, field
from typing import ClassVar


@dataclass
class Substitution:
    # Pattern to match replacements in README_FILES
    # Example: <!--replace: VARIABLE-->`content v0.1.2`
    TAG_RE_FORMAT: ClassVar[str] = r"""(?x: # re.VERBOSE to allow comments
        (?P<tag>                 # Start "tag" match group
            <!--\s*              # Begin HTML comment, followed by optional space
            replace:\s*          # "replace:" followed by optional whitespace
            {variable_name}      # The variable_name, to be filled in by str.format()
            \s*-->               # End of HTML comment, preceded by optional space
        )                        # End group
        # End re.VERBOSE, start "content" match group
        )(?P<content>{content_pattern})"""

    json_file: str
    """The JSON file, relative to project root, from which to extract a value"""

    json_key: str
    """The key of the value in `json_file`; can use dotted notation i.e. container.sub.value"""

    variable_name: str
    """The name of the variable in the `replace: VARIABLE` tag in the README or other file"""

    replacement_pattern: str
    """The regular expression in the content to be replaced with the variable value"""

    content_pattern: str = r"""(?x:
                               # In order of match preference:
        `[^`]+`                # A markdown code span: `CONTENT`
        |                      # OR
        \[[^]]+\]\([^)]+\)     # A markdown inline link: [CONTENT](CONTENT)
        |                      # OR
        \S+                    # Everything until the next space character
    )"""
    """The regular expression of the content immediately following the tag"""

    _value: str | None = field(default=None, init=False)
    """The variable value, after it is loaded by `self.load()`"""

    def __post_init__(self):
        self._tag_pattern = re.compile(
            self.TAG_RE_FORMAT.format(
                variable_name=re.escape(self.variable_name),
                content_pattern=self.content_pattern
            )
        )
        self._replacement_pattern = re.compile(self.replacement_pattern)

    def load(self):
        with open(self.json_file) as f:
            json_value = json.load(f)
        try:
            for key in self.json_key.split("."):
                json_value = json_value[key]
        except KeyError:
            raise ValueError(f"JSON key {self.json_key} does not appear in the file: {self.json_file!r}")
        self._value = str(json_value)

    def _replacer(self, match: re.Match) -> str:
        replaced_content = self._replacement_pattern.sub(self._value or "", match["content"])
        return match["tag"] + replaced_content

    def sub(self, content: str) -> str:
        if self._value is None:
            self.load()
        return self._tag_pattern.sub(self._replacer, content)


def replace_in_files(files: list[str], substitutions: list[Substitution]):
    for subst in substitutions:
        subst.load()

    for file in files:
        with open(file) as f:
            content = f.read()
        original_content = copy.copy(content)

        for subst in substitutions:
            content = subst.sub(content)

        if content != original_content:
            with open(file, "w") as f:
                f.write(content)


if __name__ == "__main__":
    README_FILES = [
        "README.md",
    ]

    REPLACEMENTS = [
        # Substitution(JSON file, JSON key (dotted notation OK), <!--replace: NAME--> in README, pattern to replace with JSON value)
        Substitution("src/libs/Karabiner-DriverKit-VirtualHIDDevice/version.json", "package_version", "VIRTUALHID_VERSION", r"\d+\.\d+\.\d+"),
        Substitution("src/libs/Karabiner-DriverKit-VirtualHIDDevice/elements-version.json", "elements_version", "ELEMENTS_VERSION", r"\d+\.\d+\.\d+")
    ]

    replace_in_files(README_FILES, REPLACEMENTS)
