"""Classes representing TEI elements.

Classes:
    Namespace: Namespaces for TEI XML elements.
    XMLElement: Represents an XML element.
    Category: Represents a <category> element.
    Bibl: Represents a <bibl> element.

Examples:
    To create a <category> element:

    >>> category = Category(
    ...     etree.Element("category", id="person"),
    ...     "person",
    ...     "A human being.",
    ... )
    >>> print(category.category_description)

    To create a <bibl> element:

    >>> bibl = Bibl(etree.Element("bibl", id="work-001"))
    >>> print(bibl.id)

    To add a <term> element to a <bibl> element:

    >>> bibl.add_term("person")
    >>> print(etree.tostring(bibl.element).decode())

    `<bibl id="work-001"><term ref="#person"/></bibl>`
"""

from dataclasses import dataclass, field

from lxml import etree


class Namespace:
    """Namespaces for TEI XML elements."""

    tei: dict[str, str] = {"tei": "http://www.tei-c.org/ns/1.0"}
    xml: dict[str, str] = {"xml": "http://www.w3.org/XML/1998/namespace"}


@dataclass
class XMLElement:
    """Represents an XML element.

    Attributes:
        element (etree.Element): The XML element.
        id (str): The xml:id attribute.
    """

    element: etree.Element
    id: str = field(default_factory=str)

    def __post_init__(self) -> None:
        self.id = self.element.get("{http://www.w3.org/XML/1998/namespace}id")


@dataclass
class Category(XMLElement):
    """Represents a <category> element.

    Attributes:
        category_description (str): The description of the category.
    """

    category_description: str = field(default_factory=str)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.category_description = self.element.findtext(
            "tei:catDesc", namespaces=Namespace.tei
        )


@dataclass
class Bibl(XMLElement):
    """
    Represents a <bibl> element.

    Attributes:
        title (str): The title of the work.

    Methods:
        add_term: Add a <term> element to a <bibl> element.
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

        Args:
            category (str): The category to reference.
        """
        self.element.append(etree.Element("term", ref=f"#{category}"))
