"""
Verifies that every @key in TEI XML manuscript descriptions
corresponds to an @xml:id in the authority files.
"""

import argparse
import sys

from tei.xml import AuthorityFile, Collections, MSDesc


def main() -> int:
    """
    Check key references in TEI XML manuscript descriptions.

    Returns 0 if all keys are valid, 1 otherwise.
    """
    parser = argparse.ArgumentParser(
        description="Check key references in TEI XML manuscript descriptions."
    )
    parser.add_argument(
        "-d",
        "--directory",
        dest="directory_path",
        nargs="?",
        default="../medieval-mss/collections",
        help="Path to a directory of TEI XML manuscript descriptions",
        type=str,
    )
    parser.add_argument(
        "-a",
        "--authority",
        dest="authority_paths",
        nargs="*",
        default=[
            "../medieval-mss/persons.xml",
            "../medieval-mss/places.xml",
            "../medieval-mss/works.xml",
        ],
        help="Paths to authority files",
        type=str,
    )
    args: argparse.Namespace = parser.parse_args()

    # create a set of all keys in the authority files
    authority_keys: set[str] = set()
    for authority_path in args.authority_paths:
        authority_keys |= AuthorityFile(authority_path).keys

    # check keys in the manuscript descriptions
    msdesc_paths: list[str] = Collections(args.directory_path).xml_paths
    results: list[bool] = [
        MSDesc(msdesc_path).check_keys(authority_keys) for msdesc_path in msdesc_paths
    ]

    if all(results):
        return 0
    else:
        print(f"{len(results) - sum(results)} errors found")
        return 1


if __name__ == "__main__":
    sys.exit(main())
