"""Classes for manipulating TEI XML files."""

import os
import re
import sys

from lxml import etree

from tei.elements import Category, Namespace


class XMLFile:
    """Represents an XML file, with methods for reading and writing."""

    def __init__(self, file_path: str) -> None:
        self.file_path: str = file_path
        self.tree: etree.ElementTree = self.read()

    def read(self) -> etree.ElementTree:
        """Create an XML tree from a file."""
        return etree.parse(
            self.file_path,
            parser=etree.XMLParser(ns_clean=True),
        )

    def write(self) -> None:
        """
        Write the XML tree to the file
        with minimal changes to formatting.
        """
        self.tree.write(
            self.file_path,
            encoding="utf-8",
            pretty_print=True,
            xml_declaration=True,
        )

        self._fix_xml_declaration()

    def _fix_xml_declaration(self) -> None:
        """Fix the XML declaration with single quotes from lxml."""
        with open(self.file_path, "r+", encoding="utf-8") as file:
            file.seek(0)
            file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            file.seek(0, 2)
            file.truncate()


class AuthorityFile(XMLFile):
    """Represents an authority file (persons.xml, places.xml, or works.xml)."""

    @property
    def keys(self) -> set[str]:
        """
        Returns a set of all xml:id attributes
        on <person>, <place>, <org>, and <bibl> elements.
        """
        return {
            elem.get("{http://www.w3.org/XML/1998/namespace}id")
            for elem in self.tree.iter(
                "{http://www.tei-c.org/ns/1.0}person",
                "{http://www.tei-c.org/ns/1.0}place",
                "{http://www.tei-c.org/ns/1.0}org",
                "{http://www.tei-c.org/ns/1.0}bibl",
            )
        }


class WorksFile(AuthorityFile):
    """Represents the works file."""

    @property
    def categories(self) -> list[Category]:
        """Return a list of Category objects."""
        return [
            Category(category)
            for category in self.tree.xpath(
                "//tei:category", namespaces=Namespace.tei
            )
        ]


class Collections:
    """Represents a directory of TEI XML manuscript descriptions."""

    def __init__(self, directory_path: str) -> None:
        self.directory_path: str = directory_path

    @property
    def paths(self) -> list[str]:
        """Returns a list of XML files in the directory."""
        return [
            os.path.join(root, file)
            for root, _, files in os.walk(self.directory_path)
            for file in files
            if file.endswith(".xml")
        ]


class MSDesc(XMLFile):
    """Represents a TEI XML manuscript description."""

    def check_keys(self, authority_keys: set[str]) -> bool:
        """Returns True if every @key reference is valid, False otherwise."""
        keys_valid: bool = True
        for key_elem in self.tree.xpath("//@key/parent::*"):
            line_number: int = key_elem.sourceline
            key: str = key_elem.get("key")

            # is the key empty?
            if key == "":
                sys.stderr.write(
                    "Error: empty key in "
                    + self.file_path
                    + ", line "
                    + str(line_number)
                    + "\n"
                )
                keys_valid = False
            # is the key in the form of `prefix_1234`?
            elif not re.match(r"\w+_\d+", key):
                sys.stderr.write(
                    "Error: "
                    + key
                    + " is invalid in "
                    + self.file_path
                    + ", line "
                    + str(line_number)
                    + "\n"
                )
                keys_valid = False
            # is the key in the authority files?
            elif key not in authority_keys:
                sys.stderr.write(
                    "Error: "
                    + key
                    + " not found in authority files in "
                    + self.file_path
                    + ", line "
                    + str(line_number)
                    + "\n"
                )
                keys_valid = False

        return keys_valid
