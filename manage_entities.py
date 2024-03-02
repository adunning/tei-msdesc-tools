"""Manage entities in TEI XML manuscript descriptions.

This script checks key references in TEI XML manuscript descriptions
against authority files and prints a summary of the results. It also
attempts to add missing records from VIAF, updating the authority files
in place.

The script can be run with default paths, which assumes that manuscript
description repository is a sibling of the current directory. The paths can
also be set with command line arguments. XPath expressions can be set to
specify the location of the VIAF records within the authority files.

Examples:
    $ python manage_entities.py
    $ python manage_entities.py -c ../medieval-mss/collections
"""

import argparse
import sys

from lxml import etree

from tei.elements import Namespace
from tei.xml import AuthorityFile, Collections, MSDesc
from viaf import VIAF


def main() -> int:
    """
    Main function for managing entities in TEI XML manuscript descriptions.

    Parses command line arguments, validates keys, adds missing records,
    and summarizes the results.

    Returns:
        int: Exit code, 0 if all keys are valid, 1 if there are invalid keys.
    """
    parser = argparse.ArgumentParser(
        description=__doc__.strip(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-v",
        "--validate",
        dest="validate_only",
        action="store_true",
        help="validate keys without adding missing records",
    )
    parser.add_argument(
        "-c",
        "--collections",
        dest="collections_path",
        nargs="?",
        default="../medieval-mss/collections",
        help="path to a directory of TEI XML manuscript descriptions",
        type=str,
    )
    parser.add_argument(
        "-l",
        "--locations",
        "--places",
        dest="places_file",
        nargs="*",
        default="../medieval-mss/places.xml",
        help="TEI XML file containing <place> elements",
        type=str,
    )
    # parser.add_argument(
    #     "-ll",
    #     "--locations-local",
    #     dest="locations_local_xpath",
    #     nargs="?",
    #     default="//tei:listPlace[@type='local']",
    #     help="XPath of container for local <place> elements",
    #     type=str,
    # )
    # parser.add_argument(
    #     "-lg",
    #     "--locations-geonames",
    #     "--places-geonames",
    #     dest="locations_geonames_xpath",
    #     nargs="?",
    #     default="//tei:listPlace[@type='geonames']",
    #     help="XPath of container for GeoNames <place> elements",
    #     type=str,
    # )
    # parser.add_argument(
    #     "-lt",
    #     "--locations-tgn",
    #     "--places-tgn",
    #     dest="locations_tgn_xpath",
    #     nargs="?",
    #     default="//tei:listPlace[@type='TGN']",
    #     help="XPath of container for TGN <place> elements",
    #     type=str,
    # )
    parser.add_argument(
        "-o",
        "--organizations",
        dest="organizations_file",
        nargs="?",
        default="../medieval-mss/places.xml",
        help="TEI XML file containing <org> elements",
        type=str,
    )
    # parser.add_argument(
    #     "-ol",
    #     "--organizations-local",
    #     dest="organizations_local_xpath",
    #     nargs="?",
    #     default="//tei:listOrg[@type='local']",
    #     help="XPath of container for local <org> elements",
    #     type=str,
    # )
    parser.add_argument(
        "-ov",
        "--organizations-viaf",
        dest="organizations_viaf_xpath",
        nargs="?",
        default="//tei:listOrg[@type='VIAF']",
        help="XPath of container for VIAF <org> elements",
        type=str,
    )
    parser.add_argument(
        "-p",
        "--persons",
        dest="persons_file",
        nargs="?",
        default="../medieval-mss/persons.xml",
        help="TEI XML file containing <person> elements",
        type=str,
    )
    # parser.add_argument(
    #     "-pl",
    #     "--persons-local",
    #     dest="persons_local_xpath",
    #     nargs="?",
    #     default="//tei:listPerson[@type='local']",
    #     help="XPath of container for local <person> elements",
    #     type=str,
    # )
    parser.add_argument(
        "-pv",
        "--persons-viaf",
        dest="persons_viaf_xpath",
        nargs="?",
        default="//tei:listPerson[@type='VIAF']",
        help="XPath of container for VIAF <person> elements",
        type=str,
    )
    parser.add_argument(
        "-w",
        "--works",
        dest="works_file",
        nargs="*",
        default="../medieval-mss/works.xml",
        help="TEI XML file containing the <bibl> elements",
        type=str,
    )
    # parser.add_argument(
    #     "-wn",
    #     "--works-anonymous",
    #     dest="works_anonymous_xpath",
    #     nargs="?",
    #     default="//tei:listBibl[@type='anonymous']",
    #     help="XPath of container for <bibl> elements without authors",
    #     type=str,
    # )
    # parser.add_argument(
    #     "-wa",
    #     "--works-authors",
    #     dest="works_authors_xpath",
    #     nargs="?",
    #     default="//tei:listBibl[@type='authors']",
    #     help="XPath of container for <bibl> elements with authors",
    #     type=str,
    # )
    args: argparse.Namespace = parser.parse_args()

    # Create a set of all keys in the authority files
    authority_keys: set[str] = set()
    authority_paths: list[str] = [
        args.organizations_file,
        args.persons_file,
        args.places_file,
        args.works_file,
    ]
    for authority_path in authority_paths:
        authority_keys |= AuthorityFile(authority_path).keys

    # Create a set of keys in the manuscript descriptions not in authorities
    missing_keys: set[str] = {
        key
        for path in Collections(args.collections_path).paths
        for key in MSDesc(path).check_keys(authority_keys)
    }

    # Create a set of likely VIAF IDs from person and organization keys
    viaf_ids: set[int] = set()
    if missing_keys and not args.validate_only:
        viaf_ids = {int(key.split("_")[-1]) for key in missing_keys}

    # Attempt to add missing VIAF records
    new_authority_keys: set[str] = set()
    persons_modified, organizations_modified = False, False
    if viaf_ids:
        # Open the authority files
        persons = AuthorityFile(args.persons_file)
        organizations = AuthorityFile(args.organizations_file)

        # Look for new VIAF records
        for viaf_id in viaf_ids:
            viaf = VIAF(viaf_id)
            element = viaf.create_element()
            if element is None:
                continue

            if element.tag == "person":
                viaf_container = persons.tree.xpath(
                    args.persons_viaf_xpath, namespaces=Namespace.tei
                )[0]
                viaf_container.append(element)
                persons.write()
                persons_modified = True
                new_authority_keys.add(
                    element.attrib["{http://www.w3.org/XML/1998/namespace}id"]
                )

            elif element.tag == "org":
                viaf_container = organizations.tree.xpath(
                    args.organizations_viaf_xpath, namespaces=Namespace.tei
                )[0]
                viaf_container.append(element)
                organizations.write()
                organizations_modified = True
                new_authority_keys.add(
                    element.attrib["{http://www.w3.org/XML/1998/namespace}id"]
                )

    # Reindent the authority files
    if persons_modified:
        etree.indent(persons.tree, space="   ")
        persons.write()
    if organizations_modified:
        etree.indent(organizations.tree, space="   ")
        organizations.write()

    # Remove the new keys from the missing keys
    missing_keys -= new_authority_keys

    # Summarize the results
    if new_authority_keys:
        print("\nAdded records:")
        for key in new_authority_keys:
            print(f"{key} from https://viaf.org/viaf/{key.split('_')[-1]}")

    if missing_keys:
        if args.validate_only:
            print("\nInvalid keys found:")
        else:
            print("\nRemaining invalid keys:")

        for key in missing_keys:
            print(key)
        return 1

    if not new_authority_keys and not missing_keys:
        print("All keys are valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
