"""
Check key references in TEI XML manuscript descriptions

Verifies that every @key in TEI XML manuscript descriptions
corresponds to an @xml:id in the authority files.
"""

import argparse
import sys

from tei.xml import AuthorityFile, Collections, MSDesc


def main() -> int:
    """
    Main function that calls the check_keys method of the MSDesc class.

    Returns 0 if all keys are valid, 1 otherwise.
    """
    parser = argparse.ArgumentParser(
        description=__doc__.strip(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
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
        type=argparse.FileType('r'),
    )
    args: argparse.Namespace = parser.parse_args()

    # create a set of all keys in the authority files
    authority_keys: set[str] = set()
    for authority_path in args.authority_paths:
        authority_keys |= AuthorityFile(authority_path).keys

    # check keys in the manuscript descriptions
    results: list[tuple[bool, list[str]]] = [
        MSDesc(path).check_keys(authority_keys)
        for path in Collections(args.directory_path).paths
    ]

    # print a summary of the results
    # and return 0 if all keys are valid, 1 otherwise

    print()
    if all(result[0] for result in results):
        print("All keys are valid.")
        return 0
    else:
        print("Missing keys:")
        print(" ".join(key for result in results for key in result[1]))
        return 1


if __name__ == "__main__":
    sys.exit(main())
