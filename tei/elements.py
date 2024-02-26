"""Classes representing TEI elements."""

from dataclasses import dataclass, field

from lxml import etree


class Namespace:
    """Namespaces for TEI XML elements."""

    tei: dict[str, str] = {"tei": "http://www.tei-c.org/ns/1.0"}
    xml: dict[str, str] = {"xml": "http://www.w3.org/XML/1998/namespace"}


@dataclass
class XMLElement:
    """Represents an XML element."""

    element: etree.Element
    id: str = field(default_factory=str)

    def __post_init__(self) -> None:
        self.id = self.element.get("{http://www.w3.org/XML/1998/namespace}id")


@dataclass
class Category(XMLElement):
    """Represents a <category> element."""

    catDesc: str = field(default_factory=str)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.catDesc = self.element.findtext(
            "tei:catDesc", namespaces=Namespace.tei
        )


@dataclass
class Bibl(XMLElement):
    """
    Represents a <bibl> element,
    with a method for adding a <term> element.
    """

    title: str = field(default_factory=str)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.title = ", ".join(
            title.text
            for title in self.element.findall(
                "tei:title", namespaces=Namespace.tei
            )
        )

    def add_term(self, category: str) -> None:
        """
        Add a <term> element to a <bibl> element,
        with a reference to a category.
        """
        self.element.append(etree.Element("term", ref=f"#{category}"))
