"""Classes for manipulating XML files."""

from lxml import etree

from .elements import Category

NS: dict[str, str] = {"tei": "http://www.tei-c.org/ns/1.0"}


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
        """Write the XML tree to the file with minimal changes to formatting."""
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


class WorksFile(XMLFile):
    """Represents the works file."""

    @property
    def categories(self) -> list[Category]:
        """Return a list of Category objects."""
        return [
            Category(category)
            for category in self.tree.xpath("//tei:category", namespaces=NS)
        ]
