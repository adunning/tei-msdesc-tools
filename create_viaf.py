"""
Create authority entries in TEI XML format based on a VIAF ID.
"""

import argparse
import re
import sys

from lxml import etree

from viaf import VIAF


def main() -> int:
    """
    Create TEI XML authority entries based on VIAF IDs.
    """
    parser = argparse.ArgumentParser(
        description="Create TEI XML authority entries based on VIAF IDs."
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

    return 0


if __name__ == "__main__":
    sys.exit(main())
