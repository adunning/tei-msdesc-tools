"""VIAF (Virtual International Authority File) data class.

This module contains a data class representing a VIAF (Virtual International
Authority File) entity. The class retrieves data from the VIAF API based on the
VIAF ID and parses the data into a structured format. The class also provides
a method to create a TEI XML element based on the VIAF data.

Example:
    To create a VIAF entity based on a VIAF ID and create a TEI XML element
    based on the VIAF data:

    >>> viaf = VIAF(34512366)
    >>> element = viaf.create_element()
    >>> print(etree.tostring(element, pretty_print=True).decode("utf-8"))

    This will output the TEI XML element representing the VIAF entity.
"""

import re
import sys
from dataclasses import dataclass, field

import requests
from lxml import etree


@dataclass
class VIAF:
    """Represents a VIAF entity.

    Attributes:
        viaf_id (int): The VIAF ID.
        name_type (str): The type of name (Personal or Corporate).
        sources (list[dict[str, str]]): The sources of the entity.
        headings (list[dict[str, str]]): The main headings of the entity.
        headings_structured (list): The structured main headings of the entity.
        name_variants (list): The name variants of the entity.
        birth_date (str): The birth date of the entity.
        death_date (str): The death date of the entity.
        date_type (str): The type of date (lived, circa, or flourished).

    Methods:
        fetch_data: Retrieves data from VIAF API based on the VIAF ID.
        format_date: Formats the date by adding leading zeroes to the year
            if less than 4 digits.
        parse_data: Parses the data retrieved from the VIAF API.
        create_element: Create an XML element based on the VIAF data.
    """

    viaf_id: int | None
    name_type: str = field(default_factory=str)
    sources: list[dict[str, str]] = field(default_factory=list)
    headings: list[dict[str, str]] = field(default_factory=list)
    headings_structured: list = field(default_factory=list)
    name_variants: list = field(default_factory=list)
    birth_date: str = field(default_factory=str)
    death_date: str = field(default_factory=str)
    date_type: str = field(default_factory=str)
    gender: str = field(default_factory=str)
    languages: list[dict[str, str]] = field(default_factory=list)
    nationalities: list[dict[str, str]] = field(default_factory=list)
    occupations: list[dict[str, str]] = field(default_factory=list)

    def __post_init__(self):
        """Initialize the VIAF entity based on the VIAF ID."""
        if not re.match(r"[1-9]\d(\d{0,7}|\d{17,20})", str(self.viaf_id)):
            sys.stderr.write("VIAF ID is invalid.")
            return
        self.data = self.fetch_data()
        self.parse_data()

    def fetch_data(self) -> dict[str, str] | None:
        """Retrieve data from VIAF JSON based on the VIAF ID."""
        url = f"https://www.viaf.org/viaf/{self.viaf_id}/viaf.json"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            if (
                response.json().get("ns0")
                == "http://viaf.org/viaf/abandonedViafRecord"
            ):
                if response.json()["scavenged"]:
                    sys.stderr.write(
                        f"VIAF ID {self.viaf_id} is a deleted record.\n"
                    )
                    self.viaf_id = None
                    return None
                elif response.json()["redirect"]:
                    sys.stderr.write(
                        f"VIAF ID {self.viaf_id} is a redirect to "
                        f"{response.json()["redirect"]["directto"]}.\n"
                    )
                    self.viaf_id = int(response.json()["redirect"]["directto"])
                    return self.fetch_data()

            return response.json()
        except requests.exceptions.RequestException as err:
            if response.status_code == 404:
                sys.stderr.write(f"VIAF ID does not exist: {self.viaf_id}\n")
                self.viaf_id = None
            else:
                sys.stderr.write(f"Request Exception: {err}")

        return None

    def format_date(self, date: str) -> str | None:
        """Ensure that the year is 4 digits long for ISO 8601."""
        if date == "0000" or date == "0":
            return None
        elif date.startswith("-"):
            date = re.sub(
                r"^(-?\d+)(-|$)",
                lambda match: match.group(1).zfill(5) + match.group(2),
                date,
            )
        else:
            date = re.sub(
                r"^(\d+)(-|$)",
                lambda match: match.group(1).zfill(4) + match.group(2),
                date,
            )
        return date

    def parse_data(self):
        """Parse data retrieved from the VIAF API."""
        if self.data is None:
            return

        self.name_type = self.data["nameType"]

        if self.data.get("sources"):
            # If there is only one source, convert it to a list
            if isinstance(self.data.get("sources")["source"], dict):
                self.data.get("sources")["source"] = [
                    self.data.get("sources").get("source")
                ]
            for source in self.data.get("sources")["source"]:
                # Split the source name and ID on the pipe character
                source_name, source_id = source["#text"].split("|")
                # Remove spaces from the source ID
                source_id = source_id.replace(" ", "")
                self.sources.append({"name": source_name, "id": source_id})

        if self.data.get("mainHeadings"):
            if isinstance(self.data.get("mainHeadings")["data"], dict):
                self.data.get("mainHeadings")["data"] = [
                    self.data.get("mainHeadings").get("data")
                ]
            for heading in self.data.get("mainHeadings")["data"]:
                # Remove repeated spaces
                heading["text"] = re.sub(r"\s+", " ", heading["text"])

                # Replace hyphens with en dashes in dates
                heading["text"] = re.sub(r"(\d+)-", r"\1–", heading["text"])
                heading["text"] = re.sub(r"-(\d+)", r"–\1", heading["text"])

                # Remove any trailing full stop
                if heading["text"].endswith("."):
                    heading["text"] = heading["text"][:-1]

                self.headings.append(
                    {
                        "text": heading["text"],
                        "sources": heading["sources"]["s"],
                    }
                )

        if self.data.get("mainHeadings")["mainHeadingEl"]:
            if isinstance(
                self.data.get("mainHeadings")["mainHeadingEl"], dict
            ):
                self.data.get("mainHeadings")["mainHeadingEl"] = [
                    self.data.get("mainHeadings")["mainHeadingEl"]
                ]
            for heading in self.data.get("mainHeadings")["mainHeadingEl"]:
                for subfield in heading["datafield"]["subfield"]:
                    if isinstance(heading["datafield"]["subfield"], dict):
                        heading["datafield"]["subfield"] = [
                            heading["datafield"]["subfield"]
                        ]
                # Remove trailing punctuation from subfields
                for subfield in heading["datafield"]["subfield"]:
                    if subfield["#text"].endswith((".", ",")):
                        subfield["#text"] = subfield["#text"][:-1]
                self.headings_structured.append(
                    {
                        "dtype": heading["datafield"]["@dtype"],
                        "ind1": heading["datafield"]["@ind1"],
                        "ind2": heading["datafield"]["@ind2"],
                        "tag": heading["datafield"]["@tag"],
                        "subfields": [
                            {
                                "code": subfield["@code"],
                                "text": subfield["#text"],
                            }
                            for subfield in heading["datafield"]["subfield"]
                        ],
                        "sources": heading["sources"]["s"],
                    }
                )

        if self.data.get("x400s"):
            if isinstance(self.data.get("x400s")["x400"], dict):
                self.data.get("x400s")["x400"] = [
                    self.data.get("x400s").get("x400")
                ]
            for heading in self.data.get("x400s")["x400"]:
                for subfield in heading["datafield"]["subfield"]:
                    if isinstance(heading["datafield"]["subfield"], dict):
                        heading["datafield"]["subfield"] = [
                            heading["datafield"]["subfield"]
                        ]
                # Remove trailing punctuation from subfields
                for subfield in heading["datafield"]["subfield"]:
                    if subfield["#text"].endswith((".", ",")):
                        subfield["#text"] = subfield["#text"][:-1]
                self.name_variants.append(
                    {
                        "dtype": heading["datafield"]["@dtype"],
                        "ind1": heading["datafield"]["@ind1"],
                        "ind2": heading["datafield"]["@ind2"],
                        "tag": heading["datafield"]["@tag"],
                        "subfields": [
                            {
                                "code": subfield["@code"],
                                "text": subfield["#text"],
                            }
                            for subfield in heading["datafield"]["subfield"]
                        ],
                        "sources": heading["sources"]["s"],
                    }
                )

        # Format the birth and death dates for ISO 8601
        self.birth_date = self.format_date(self.data["birthDate"])
        self.death_date = self.format_date(self.data["deathDate"])
        self.date_type = self.data["dateType"]

        gender_type = self.data["fixed"]["gender"]
        if gender_type == "a":
            gender_type = "female"
        elif gender_type == "b":
            gender_type = "male"
        else:
            gender_type = None
        self.gender = gender_type

        if self.data.get("languageOfEntity"):
            if isinstance(self.data.get("languageOfEntity")["data"], dict):
                self.data.get("languageOfEntity")["data"] = [
                    self.data.get("languageOfEntity").get("data")
                ]
            for language in self.data["languageOfEntity"]["data"]:
                self.languages.append(
                    {
                        "language": language["text"],
                        "sources": language["sources"]["s"],
                    }
                )

        if self.data.get("nationalityOfEntity"):
            if isinstance(self.data.get("nationalityOfEntity")["data"], dict):
                self.data.get("nationalityOfEntity")["data"] = [
                    self.data.get("nationalityOfEntity").get("data")
                ]
            for nationality in self.data["nationalityOfEntity"]["data"]:
                self.nationalities.append(
                    {
                        "nationality": nationality["text"],
                        "sources": nationality["sources"]["s"],
                    }
                )

        if self.data.get("occupation"):
            if isinstance(self.data.get("occupation")["data"], dict):
                self.data.get("occupation")["data"] = [
                    self.data.get("occupation").get("data")
                ]
            for occupation in self.data["occupation"]["data"]:
                self.occupations.append(
                    {
                        "occupation": occupation["text"],
                        "sources": occupation["sources"]["s"],
                    }
                )

    def create_element(self) -> etree.Element:
        """Create an XML element based on the VIAF data.

        Returns:
            etree.Element: The XML element representing the VIAF entity.
        """
        # If there is no data due to an error, return None
        if self.data is None:
            return None

        # Create the element
        if self.name_type == "Personal":
            element_name: str = "person"
            element_id: str = f"person_{self.viaf_id}"
        elif self.name_type == "Corporate":
            element_name = "org"
            element_id = f"org_{self.viaf_id}"

        # Set the element id
        element = etree.Element(
            element_name, nsmap={"xml": "http://www.w3.org/XML/1998/namespace"}
        )
        element.set("{http://www.w3.org/XML/1998/namespace}id", element_id)

        # Find a display heading by looking for a preferred source
        display_heading = next(
            (
                heading
                for heading in self.headings
                if "LC" in heading["sources"]
            ),
            None,
        )
        if display_heading is None:
            display_heading = next(
                (
                    heading
                    for heading in self.headings
                    if "DNB" in heading["sources"]
                ),
                None,
            )
        if display_heading is None:
            display_heading = next(
                (
                    heading
                    for heading in self.headings
                    if "BNF" in heading["sources"]
                    or "SUDOC" in heading["sources"]
                    or "BIBSYS" in heading["sources"]
                    or "NTA" in heading["sources"]
                    or "JPG" in heading["sources"]
                ),
                None,
            )
        # If there is no preferred source, use the one with the most sources
        if display_heading is None:
            display_heading = max(
                self.headings, key=lambda heading: len(heading["sources"])
            )
        # If there is still no display heading, use the first one
        if display_heading is None:
            display_heading = self.headings[0]

        # Add the display heading to the element
        if element_name == "person":
            display_element = etree.SubElement(element, "persName")
        elif element_name == "org":
            display_element = etree.SubElement(element, "orgName")
        display_element.set(
            "source",
            " ".join(display_heading["sources"])
            if isinstance(display_heading["sources"], list)
            else display_heading["sources"],
        )
        display_element.set("type", "display")
        display_element.text = display_heading["text"]

        # Create filtered lists of the structured headings and name variants
        headings_preferred = [
            heading
            for heading in self.headings_structured
            if any(
                source in heading["sources"]
                for source in ["LC", "DNB", "BNF", "BAV", "JPG"]
            )
        ]
        variants_preferred = [
            variant
            for variant in self.name_variants
            if any(
                source in variant["sources"]
                for source in ["LC", "DNB", "BNF", "BAV", "JPG"]
            )
        ]

        # Add a normalized string to each list from the subfields
        for heading in headings_preferred + variants_preferred:
            heading["normalized"] = " ".join(
                subfield["text"]
                for subfield in heading["subfields"]
                if subfield["code"].isalpha()
            ).strip()

        for heading in headings_preferred + variants_preferred:
            heading["normalized"] = "".join(
                char for char in heading["normalized"] if char.isalpha()
            )

        # Deduplicate headings_preferred as structured_names
        structured_names = []
        normalized_strings = set()
        for heading in headings_preferred:
            normalized_string = heading["normalized"]
            if normalized_string not in normalized_strings:
                structured_names.append(heading)
                normalized_strings.add(normalized_string)
        # Add the name variants to the structured names
        for variant in variants_preferred:
            normalized_string = variant["normalized"]
            if normalized_string not in normalized_strings:
                structured_names.append(variant)
                normalized_strings.add(normalized_string)

        # Encode structured name variants
        for name in structured_names:
            if element_name == "person":
                variant_element = etree.SubElement(element, "persName")
            elif element_name == "org":
                variant_element = etree.SubElement(element, "orgName")
            variant_element.set(
                "source",
                " ".join(name["sources"])
                if isinstance(name["sources"], list)
                else name["sources"],
            )
            variant_element.set("type", "variant")
            if name["ind1"] == "0":
                variant_element.set("subtype", "forenameFirst")
            elif name["ind1"] == "1":
                variant_element.set("subtype", "surnameFirst")
            # print each of the subfields within a <name> element
            for subfield in name["subfields"]:
                if not subfield["code"].isalpha():
                    continue
                name_element = etree.SubElement(variant_element, "name")
                name_element.set("type", f"marc-{subfield["code"]}")
                name_element.text = subfield["text"]

        # Set the birth and death dates
        if self.date_type == "lived":
            if self.birth_date:
                birth = etree.SubElement(element, "birth")
                birth.set("source", "VIAF")
                birth.set("when", self.birth_date)
            if self.death_date:
                death = etree.SubElement(element, "death")
                death.set("source", "VIAF")
                death.set("when", self.death_date)
        elif self.date_type == "circa":
            if self.birth_date:
                birth = etree.SubElement(element, "birth")
                birth.set("cert", "low")
                birth.set("source", "VIAF")
                birth.set("when", self.birth_date)
            if self.death_date:
                death = etree.SubElement(element, "death")
                death.set("cert", "low")
                death.set("source", "VIAF")
                death.set("when", self.death_date)
        elif self.date_type == "flourished":
            flourished = etree.SubElement(element, "floruit")
            flourished.set("source", "VIAF")
            if self.birth_date:
                flourished.set("notBefore", self.birth_date)
            if self.death_date:
                flourished.set("notAfter", self.death_date)

        if element_name == "person":
            if self.gender:
                sex = etree.SubElement(element, "sex")
                sex.set("source", "VIAF")
                sex.text = self.gender

            if self.languages:
                for language in self.languages:
                    language_element = etree.SubElement(element, "langKnown")
                    language_element.set(
                        "source",
                        " ".join(language["sources"])
                        if isinstance(language["sources"], list)
                        else language["sources"],
                    )
                    language_element.set("tag", language["language"])

            if self.nationalities:
                for nationality in self.nationalities:
                    nationality_element = etree.SubElement(
                        element, "nationality"
                    )
                    nationality_element.set(
                        "source",
                        " ".join(nationality["sources"])
                        if isinstance(nationality["sources"], list)
                        else nationality["sources"],
                    )
                    nationality_element.text = nationality["nationality"]

            if self.occupations:
                for occupation in self.occupations:
                    occupation_element = etree.SubElement(
                        element, "occupation"
                    )
                    occupation_element.set(
                        "source",
                        " ".join(occupation["sources"])
                        if isinstance(occupation["sources"], list)
                        else occupation["sources"],
                    )
                    occupation_element.text = occupation["occupation"]

        # Create a list of links
        note = etree.SubElement(element, "note")
        note.set("type", "links")
        link_list = etree.SubElement(note, "list")
        link_list.set("type", "links")

        for source in self.sources:
            viaf_sources = {
                "BNF": {
                    "url": f"https://data.bnf.fr/en/{source["id"]}",
                    "title": "BNF",
                },
                "DNB": {
                    "url": f"https://d-nb.info/gnd/{source["id"]}",
                    "title": "GND",
                },
                "ISNI": {
                    "url": f"https://isni.org/isni/{source["id"]}",
                    "title": "ISNI",
                },
                "LC": {
                    "url": "https://id.loc.gov/authorities/names/"
                    + f"{source["id"]}",
                    "title": "LC",
                },
                "WKP": {
                    "url": f"https://wikidata.org/wiki/{source["id"]}",
                    "title": "Wikidata",
                },
            }

            if source["name"] in viaf_sources:
                item = etree.SubElement(link_list, "item")
                ref = etree.SubElement(item, "ref")
                ref.set("target", viaf_sources[source["name"]]["url"])
                title = etree.SubElement(ref, "title")
                title.text = viaf_sources[source["name"]]["title"]

        viaf_item = etree.SubElement(link_list, "item")
        viaf_ref = etree.SubElement(viaf_item, "ref")
        viaf_ref.set("target", f"https://viaf.org/viaf/{self.viaf_id}")
        viaf_title = etree.SubElement(viaf_ref, "title")
        viaf_title.text = "VIAF"

        # Sort the resulting list of links by title
        link_list[:] = sorted(
            link_list, key=lambda item: item[0][0].text or ""
        )

        return element
