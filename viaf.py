"""
Module for working with VIAF data.
"""

import re
import sys
from dataclasses import dataclass, field

import requests
from lxml import etree


@dataclass
class VIAF:
    """
    Class representing a VIAF (Virtual International Authority File) entity.

    Attributes:
        viaf_id (int): The VIAF ID of the entity.
        data (dict): The data retrieved from the VIAF API.

    Methods:
        fetch_data(self): Retrieves data from the VIAF API.
        create_element(self): Creates an XML element based on the VIAF data.
    """

    viaf_id: int
    name_type: str = field(default_factory=str)
    sources: list = field(default_factory=list)
    headings: list = field(default_factory=list)
    headings_structured: list = field(default_factory=list)
    name_variants: list = field(default_factory=list)
    birth_date: str = field(default_factory=str)
    death_date: str = field(default_factory=str)
    date_type: str = field(default_factory=str)
    gender: str = field(default_factory=str)
    languages: list = field(default_factory=list)
    nationalities: list = field(default_factory=list)
    occupations: list = field(default_factory=list)

    def __post_init__(self) -> None:
        if not re.match(r"[1-9]\d(\d{0,7}|\d{17,20})", str(self.viaf_id)):
            sys.stderr.write("VIAF ID is invalid.")
            return
        self.data = self.fetch_data()
        self.parse_data()

    def fetch_data(self) -> dict[str, any]:
        """
        Retrieves data from VIAF API based on the VIAF ID.
        """
        url = f"https://www.viaf.org/viaf/{self.viaf_id}/viaf.json"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            if (
                response.json().get("ns0")
                == "http://viaf.org/viaf/abandonedViafRecord"
            ):
                sys.stderr.write(
                    f"VIAF ID {self.viaf_id} is a redirect to "
                    f"{response.json()['redirect']['directto']}\n"
                )
                self.viaf_id = int(
                    response.json()["redirect"]["directto"]
                )
                return self.fetch_data()
            return response.json()
        except requests.exceptions.RequestException as err:
            if response.status_code == 404:
                sys.stderr.write(f"VIAF ID does not exist: {self.viaf_id}\n")
                self.viaf_id = None
                return
            else:
                sys.stderr.write(f"Request Exception: {err}")
                return

    def format_date(self, date: str) -> str:
        """
        Formats the date by adding leading zeroes to the year
        if less than 4 digits.
        """
        date = re.sub(
            r"^(\d+)(-|$)",
            lambda match: match.group(1).zfill(4) + match.group(2),
            date,
        )
        if date == "0000":
            return None
        return date

    def parse_data(self) -> None:
        """
        Parses the data retrieved from the VIAF API.
        """
        if self.data is None:
            return

        self.name_type = self.data["nameType"]

        if self.data.get("sources") is not None:
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
                self.sources.append(
                    {"name": source_name, "id": source_id}
                )

        if self.data.get("mainHeadings") is not None:
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

        if self.data.get("mainHeadings")["mainHeadingEl"] is not None:
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
                self.headings_structured.append(
                    {
                        "dtype": heading["datafield"]["@dtype"],
                        "ind1": heading["datafield"]["@ind1"],
                        "ind2": heading["datafield"]["@ind2"],
                        "tag": heading["datafield"]["@tag"],
                        "subfields": [
                            {
                                "code": subfield["@code"],
                                "text": subfield["#text"]
                            }
                            for subfield in heading["datafield"]["subfield"]
                        ],
                        "sources": heading["sources"]["s"],
                    }
                )

        if self.data.get("x400s") is not None:
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
                self.name_variants.append(
                    {
                        "dtype": heading["datafield"]["@dtype"],
                        "ind1": heading["datafield"]["@ind1"],
                        "ind2": heading["datafield"]["@ind2"],
                        "tag": heading["datafield"]["@tag"],
                        "subfields": [
                            {
                                "code": subfield["@code"],
                                "text": subfield["#text"]
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

        if self.data.get("languageOfEntity") is not None:
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

        if self.data.get("nationalityOfEntity") is not None:
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

        if self.data.get("occupation") is not None:
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
        """
        Create an XML element based on the VIAF data.

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
            element_name: str = "org"
            element_id: str = f"org_{self.viaf_id}"

        # Set the element id
        element = etree.Element(
            element_name, nsmap={"xml": "http://www.w3.org/XML/1998/namespace"}
        )
        element.set("{http://www.w3.org/XML/1998/namespace}id", element_id)

        # Provide name variant headings
        for heading in self.headings:
            if element_name == "person":
                variant_element = etree.SubElement(element, "persName")
            elif element_name == "org":
                variant_element = etree.SubElement(element, "orgName")

            # Set the source of the variant name
            variant_element.set(
                "source",
                " ".join(heading["sources"])
                if isinstance(heading["sources"], list)
                else heading["sources"]
                )
            variant_element.set("type", "variant")
            variant_element.text = heading["text"]

        # Set the display form for the persName or orgName element
        display_form_set: bool = False
        # Prefer the LC source for the display form
        for variant_element in element.iter("persName", "orgName"):
            sources: list[str] = variant_element.get("source").split(" ")
            if "LC" in sources:
                variant_element.set("type", "display")
                display_form_set = True

        # If there is no LC source, use the DNB source
        if not display_form_set:
            for variant_element in element.iter("persName", "orgName"):
                sources: list[str] = variant_element.get("source").split(" ")
                if "DNB" in sources:
                    variant_element.set("type", "display")
                    display_form_set = True

        if not display_form_set:
            for variant_element in element.iter("persName", "orgName"):
                sources: list[str] = variant_element.get("source").split(" ")
                if any(
                    source in sources for source
                        in ["BNF", "SUDOC", "JPG"]):
                    variant_element.set("type", "display")
                    display_form_set = True

        # If there is no preferred source, use the entry with the most sources
        if not display_form_set:
            max_sources = 0

            for variant_element in element.iter("persName", "orgName"):
                sources: list[str] = variant_element.get("source").split(" ")

                if len(sources) > max_sources:
                    max_sources = len(sources)
                    variant_element.set("type", "display")
                    display_form_set = True
                elif len(sources) == max_sources:
                    display_form_set = False

        # If no name has been set as the display form, use the first one
        if not display_form_set:
            for variant_element in element.iter("persName", "orgName"):
                variant_element.set("type", "display")
                break

        # Sort name variants placing the display form first
        # element[:] = sorted(
        #     element,
        #     key=lambda variant: (
        #         variant.get("type") != "display",
        #         variant.text,
        #     ),
        # )

        # Delete all name variants that are not the display form
        for variant_element in element.iter("persName", "orgName"):
            if variant_element.get("type") != "display":
                element.remove(variant_element)

        # Provide structured name variants from headings
        for heading in self.headings_structured:
            if element_name == "person":
                variant_element = etree.SubElement(element, "persName")
            elif element_name == "org":
                variant_element = etree.SubElement(element, "orgName")
            variant_element.set(
                "source",
                " ".join(heading["sources"])
                if isinstance(heading["sources"], list)
                else heading["sources"]
                )
            variant_element.set("type", "variant")
            if heading["ind1"] == "0":
                variant_element.set("subtype", "forenameFirst")
            elif heading["ind1"] == "1":
                variant_element.set("subtype", "surnameFirst")
            # print each of the subfields within a <name> element
            for subfield in heading["subfields"]:
                if not subfield["code"].isalpha():
                    continue
                name_element = etree.SubElement(variant_element, "name")
                name_element.set("type", f"marc-{subfield["code"]}")
                name_element.text = subfield["text"]

        # Provide structured name variants from x400s
        if self.name_variants is not None:
            for name in self.name_variants:
                if element_name == "person":
                    variant_element = etree.SubElement(element, "persName")
                elif element_name == "org":
                    variant_element = etree.SubElement(element, "orgName")
                variant_element.set(
                    "source",
                    " ".join(name["sources"])
                    if isinstance(name["sources"], list)
                    else name["sources"]
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
            if self.birth_date is not None:
                birth = etree.SubElement(element, "birth")
                birth.set("source", "VIAF")
                birth.set("when", self.birth_date)
            if self.death_date is not None:
                death = etree.SubElement(element, "death")
                death.set("source", "VIAF")
                death.set("when", self.death_date)
        elif self.date_type == "circa":
            if self.birth_date is not None:
                birth = etree.SubElement(element, "birth")
                birth.set("cert", "low")
                birth.set("source", "VIAF")
                birth.set("when", self.birth_date)
            if self.death_date is not None:
                death = etree.SubElement(element, "death")
                death.set("cert", "low")
                death.set("source", "VIAF")
                death.set("when", self.death_date)
        elif self.date_type == "flourished":
            if self.birth_date is not None:
                flourished = etree.SubElement(element, "floruit")
                flourished.set("source", "VIAF")
                flourished.set("notBefore", self.birth_date)
                flourished.set("notAfter", self.death_date)

        if self.gender is not None:
            sex = etree.SubElement(element, "sex")
            sex.set("source", "VIAF")
            sex.text = self.gender

        if self.languages is not None:
            for language in self.languages:
                language_element = etree.SubElement(element, "langKnown")
                language_element.set(
                    "source",
                    " ".join(language["sources"])
                    if isinstance(language["sources"], list)
                    else language["sources"]
                )
                language_element.set("tag", language["language"])

        if self.nationalities is not None:
            for nationality in self.nationalities:
                nationality_element = etree.SubElement(element, "nationality")
                nationality_element.set(
                    "source",
                    " ".join(nationality["sources"])
                    if isinstance(nationality["sources"], list)
                    else nationality["sources"]
                )
                nationality_element.text = nationality["nationality"]

        if self.occupations is not None:
            for occupation in self.occupations:
                occupation_element = etree.SubElement(element, "occupation")
                occupation_element.set(
                    "source",
                    " ".join(occupation["sources"])
                    if isinstance(occupation["sources"], list)
                    else occupation["sources"]
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
        link_list[:] = sorted(link_list, key=lambda item: item[0][0].text)

        return element
