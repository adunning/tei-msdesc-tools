"""
Create authority entries in TEI XML format from VIAF IDs
"""

import argparse
import re
import sys

from lxml import etree

from viaf import VIAF


def main() -> int:
    """
    Main function that processes VIAF IDs and generates XML output.

    Returns:
        int: The exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(
        description=__doc__.strip(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "viaf_ids",
        nargs="+",
        help="VIAF IDs or URLs for authority entries",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output file",
    )
    args = parser.parse_args()

    viaf_ids: set[int] = {
        (
            int(re.search(r"viaf/(\d+)", viaf_id).group(1))
            if viaf_id.startswith("http")
            else int("".join(filter(str.isdigit, viaf_id)))
        )
        for viaf_id in args.viaf_ids
    }
    people: list[str] = []
    organizations: list[str] = []

    for viaf_id in viaf_ids:
        viaf = VIAF(viaf_id)
        element = viaf.create_element()
        if element is None:
            continue
        if element.tag == "person":
            people.append(
                etree.tostring(element, encoding="unicode", pretty_print=True)
            )
        elif element.tag == "org":
            organizations.append(
                etree.tostring(element, encoding="unicode", pretty_print=True)
            )

    if args.output:
        with open(args.output, "w", encoding="utf-8") as file:
            if len(people) > 0:
                file.write("<!-- People -->\n")
                file.write("\n".join(people))
            if len(organizations) > 0:
                file.write("<!-- Organizations -->\n")
                file.write("\n".join(organizations))
    else:
        if len(people) > 0:
            print("<!-- People -->")
            print("\n".join(people))
        if len(organizations) > 0:
            print("<!-- Organizations -->")
            print("\n".join(organizations))

    if len(people) == 0 and len(organizations) == 0:
        sys.stderr.write("No authority entries were created.\n")
        return 1
    else:
        return 0


if __name__ == "__main__":
    sys.exit(main())
