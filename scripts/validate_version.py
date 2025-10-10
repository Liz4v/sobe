import os
import sys
import tomllib


def main() -> None:
    # extract version from tag
    ref = os.getenv("GITHUB_REF", "")
    if not ref.startswith("refs/tags/"):
        print(f"GITHUB_REF is not a tag ref: {ref}", file=sys.stderr)
        sys.exit(1)
    tag_str = ref.removeprefix("refs/tags/")

    # extract version from pyproject.toml
    with open("pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    toml_str = data["project"]["version"]

    # compare versions
    tag_list = tag_str.split(".")
    toml_list = toml_str.split(".")
    length = min(len(tag_list), len(toml_list))
    if tag_list[:length] != toml_list[:length]:
        print(f"Tag '{tag_str}' does not match pyproject.toml version '{toml_str}'", file=sys.stderr)
        sys.exit(1)

    print("Version validation passed.")


if __name__ == "__main__":
    main()
