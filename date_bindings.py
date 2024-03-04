"""Classify dates on TEI <binding> elements.

This script processes TEI XML files and prompts the user to classify
the date of each <binding> element. The user can classify the date as
contemporary, a single year, or a date range.

Examples:
    $ python date_bindings.py
    $ python date_bindings.py -d ../medieval-mss/collections
"""

import argparse
import sys

from tei.elements import Namespace, XMLElement
from tei.xml import Collections, XMLFile


class Binding(XMLElement):
    """Represents a <binding> element in a TEI file."""

    def add_date(self) -> bool:
        """Prompts the user to input a date or mark it as contemporary.

        Modifies the element to include the appropriate attribute.

        Returns:
            bool: True if the element is modified, False if it is skipped
        """
        # print the <binding> element text
        print("".join(self.element.xpath("string()")).strip())

        date_string: str = input(
            "\nEnter ‘c’ for a contemporary binding, "
            "a date range as yyyy/yyyy, or a single year as yyyy: "
        )

        match date_string.lower():
            case "c":
                self.element.set("contemporary", "true")
                return True

            case date_string if date_string.isdigit() and len(
                date_string
            ) == 4:
                self.element.set("when", date_string)
                return True

            case date_string if "/" in date_string or "-" in date_string:
                dates: list[str] = date_string.replace("-", "/").split("/")

                if len(dates) == 2 and all(
                    date.isdigit() and len(date) == 4 for date in dates
                ):
                    self.element.set("notBefore", dates[0])
                    self.element.set("notAfter", dates[1])
                    return True

            case "":
                return False

        print("\nInvalid date format.\n")
        return self.add_date()


def main() -> int:
    """Add dates to TEI <binding> elements.

    Returns:
        int: The exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(
        description=__doc__.strip(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        dest="directory",
        nargs="?",
        default="../medieval-mss/collections",
        help="Path to the directory containing the TEI XML files",
        type=str,
    )
    args: argparse.Namespace = parser.parse_args()

    for path in Collections(args.directory).paths:
        msdesc: XMLFile = XMLFile(path)
        # process all <binding> elements without a date attribute
        for binding_element in msdesc.tree.xpath(
            "//tei:binding[not(@when) and not(@notBefore)"
            "and not(@notAfter) and not(@contemporary)]",
            namespaces=Namespace.tei,
        ):
            print(f"\n{msdesc.file_path}:\n")
            # ask the user to classify the <binding> element
            if Binding(binding_element).add_date():
                msdesc.write()
            # if the user does not enter a date, skip the element
            else:
                continue

    print("All files processed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
