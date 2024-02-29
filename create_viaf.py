"""Create authority entries in TEI XML format from VIAF IDs.

This script takes VIAF IDs or URLs for authority entries and generates
TEI XML output, producing <person> and <org> elements for each VIAF ID.

Examples:
    $ python create_viaf.py 34512366 person_69848690 org_129788129
    $ python create_viaf.py 34512366 69848690 129788129 -o output.xml
    $ python create_viaf.py https://viaf.org/viaf/34512366 > output.xml
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
        dest="viaf_ids",
        nargs="+",
        help="VIAF IDs or URLs for authority entries",
        type=str,
    )
    parser.add_argument(
        "--output",
        "-o",
        dest="output_file_path",
        help="Output file",
        type=argparse.FileType("w"),
    )
    args = parser.parse_args()

    viaf_ids: set[int] = set(
        sorted(
            (
                int(re.search(r"viaf/(\d+)", viaf_id).group(1))
                if re.search(r"viaf/(\d+)", viaf_id) is not None
                else (
                    0
                    if viaf_id.startswith("http")
                    else int("".join(filter(str.isdigit, viaf_id)))
                )
            )
            for viaf_id in args.viaf_ids
        )
    )
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

    if len(people) == 0 and len(organizations) == 0:
        sys.stderr.write("No authority entries were created.\n")
        return 1

    # If an output file is specified, write the results to the file;
    # otherwise, print to the console
    if args.output_file_path:
        output_file = args.output_file_path
    else:
        output_file = sys.stdout

    if len(people) > 0:
        output_file.write("<!-- People -->\n")
        output_file.write("\n".join(people))

    if len(organizations) > 0:
        output_file.write("<!-- Organizations -->\n")
        output_file.write("\n".join(organizations))

    if args.output_file_path:
        output_file.close()

    if len(people) == 1:
        print("\nEntry created for 1 person.")
    elif len(people) > 1:
        print(f"\nEntries created for {len(people)} people.")
    if len(organizations) == 1:
        print("Entry created for 1 organization.")
    elif len(organizations) > 1:
        print(f"Entries created for {len(organizations)} organizations.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
