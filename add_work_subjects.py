"""Add subject classifications to TEI <bibl> elements

This script prompts the user to select one or more subject classifications for
each <bibl> element in a TEI XML file. The selected classifications are added
as <term> elements within the <bibl> elements.

Examples:
    $ python add_work_subjects.py ../medieval-mss/works.xml
    $ python add_work_subjects.py -h
"""

import argparse
import sys

from tei.elements import Bibl, Category, Namespace
from tei.xml import WorksFile


class CategorySelector(list[str]):
    """Prompt the user to select a category.

    Attributes:
        bibl_title (str): The title of the <bibl> element
        categories (list[Category]): The available categories

    Methods:
        __call__: Prompt the user for input and return the selected categories
        _print_categories: Print the available categories in rows of three
    """

    def __call__(
        self, bibl_title: str, categories: list[Category]
    ) -> list[str]:
        """Return category IDs from the user's selection.

        Args:
            bibl_title (str): The title of the <bibl> element
            categories (list[Category]): The available categories

        Returns:
            list[str]: The selected category IDs
        """
        while True:
            print(f"\n{bibl_title}\n")
            self._print_categories(
                [category.category_description for category in categories]
            )
            selection: str = input("\nEnter one or more category numbers: ")
            try:
                # return a list of the category IDs from the user's selection
                return [
                    categories[int(index) - 1].id
                    for index in selection.split()
                ]
            except ValueError:
                print("Please enter one of more numbers.")
                continue
            except IndexError:
                print("Please select from the numbers listed.")
                continue

    def _print_categories(self, category_descriptions: list[str]) -> None:
        """Print the available categories in rows of three.

        Args:
            category_descriptions (list[str]): Category descriptions
        """
        for index, description in enumerate(category_descriptions, start=1):
            print(f"{index:>2}. {description:<25}", end="")
            # print a newline after every third category
            if index % 3 == 0:
                print("\n", end="")


def main() -> int:
    """Prompt the user to select a category for each <bibl> element.

    Returns:
        int: The exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(
        description=__doc__.strip(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        dest="works_file_path",
        nargs="?",
        default="../medieval-mss/works.xml",
        help="Path to the TEI XML file containing the <bibl> elements",
        type=str,
    )
    args = parser.parse_args()

    works = WorksFile(args.works_file_path)

    # Iterate over <bibl> elements with an xml:id but no <term> child
    for bibl_element in works.tree.xpath(
        "//tei:bibl[@xml:id and not(tei:term)]", namespaces=Namespace.tei
    ):
        # Create a Work object for manipulating the <bibl> element
        bibl: Bibl = Bibl(bibl_element)

        # Get the user's selection of categories
        selected_categories: list[str] = CategorySelector()(
            bibl.title, works.categories
        )

        # If there is no selection, skip to the next <bibl> element
        if not selected_categories:
            continue

        # Add <term> elements for the selected categories
        for category in selected_categories:
            bibl.add_term(category)

        # Update the XML file
        works.write()

    print("\nAll works have been processed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
