"""
Module for working with VIAF data.
"""

import re
import sys
from dataclasses import dataclass

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
    data: dict[str, any] = None

    def __post_init__(self) -> None:
        if not re.match(r"[1-9]\d(\d{0,7}|\d{17,20})", str(self.viaf_id)):
            sys.stderr.write("VIAF ID is invalid.")
        elif self.data is None:
            self.data = self.fetch_data()

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
                    f"{response.json().get('redirect').get('directto')}\n"
                )
                self.viaf_id = int(
                    response.json().get("redirect").get("directto")
                )
                return self.fetch_data()
            return response.json()
        except requests.exceptions.RequestException as err:
            if response.status_code == 404:
                sys.stderr.write(f"VIAF ID does not exist: {self.viaf_id}\n")
            else:
                sys.stderr.write(f"Request Exception: {err}")

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
        if self.data.get("nameType") == "Personal":
            element_name: str = "person"
            element_id: str = f"person_{self.viaf_id}"
        elif self.data.get("nameType") == "Corporate":
            element_name: str = "org"
            element_id: str = f"org_{self.viaf_id}"

        # Set the element id
        element = etree.Element(
            element_name, nsmap={"xml": "http://www.w3.org/XML/1998/namespace"}
        )
        element.set("{http://www.w3.org/XML/1998/namespace}id", element_id)

        # Wrap mainHeadings.data in a list if there is only one
        if isinstance(self.data.get("mainHeadings").get("data"), dict):
            self.data.get("mainHeadings")["data"] = [
                self.data.get("mainHeadings").get("data")
            ]

        # Provide name variants from mainHeadings
        for heading in self.data.get("mainHeadings").get("data"):
            if element_name == "person":
                variant_name = etree.SubElement(element, "persName")
            elif element_name == "org":
                variant_name = etree.SubElement(element, "orgName")

            # Remove repeated spaces
            heading["text"] = re.sub(r"\s+", " ", heading["text"])

            # Replace hyphens with en dashes in dates
            heading["text"] = re.sub(r"(\d+)-", r"\1–", heading["text"])
            heading["text"] = re.sub(r"-(\d+)", r"–\1", heading["text"])
            variant_name.text = heading.get("text")

            # Remove any trailing full stop
            if variant_name.text.endswith("."):
                variant_name.text = variant_name.text[:-1]

            # Set the source of the variant name
            source_list: list[str] = heading.get("sources").get("s")
            # If there is only one source, it is a string, not a list
            if isinstance(source_list, str):
                source_list = [source_list]
            source_list = " ".join(source_list)
            variant_name.set("source", source_list)
            variant_name.set("type", "variant")

        # Set the display form for the persName or orgName element
        display_form_set: bool = False
        # Prefer the LC source for the display form
        for variant_name in element.iter("persName", "orgName"):
            sources: list[str] = variant_name.get("source").split(" ")
            if "LC" in sources:
                variant_name.set("type", "display")
                display_form_set = True

        # If there is no LC source, use the DNB source
        if not display_form_set:
            for variant_name in element.iter("persName", "orgName"):
                sources: list[str] = variant_name.get("source").split(" ")
                if "DNB" in sources:
                    variant_name.set("type", "display")
                    display_form_set = True

        # If there is no LC or DNB source, use the entry with the most sources
        if not display_form_set:
            max_sources = 0

            for variant_name in element.iter("persName", "orgName"):
                sources: list[str] = variant_name.get("source").split(" ")

                if len(sources) > max_sources:
                    max_sources = len(sources)
                    variant_name.set("type", "display")
                    display_form_set = True
                elif len(sources) == max_sources:
                    display_form_set = False

        # If no name has been set as the display form, use the first one
        if not display_form_set:
            for variant_name in element.iter("persName", "orgName"):
                variant_name.set("type", "display")
                break

        # Set the birth and death dates
        if self.data.get("birthDate") != "0":
            birth = etree.SubElement(element, "birth")
            birth.set("source", "VIAF")
            birth.set("when", self.data.get("birthDate"))

        if self.data.get("deathDate") != "0":
            death = etree.SubElement(element, "death")
            death.set("source", "VIAF")
            death.set("when", self.data.get("deathDate"))

        # Add leading zeroes to the birth/death year if less than 4 digits
        for date in element.iter("birth", "death"):
            date.set(
                "when",
                re.sub(
                    r"^(\d+)(-|$)",
                    lambda match: match.group(1).zfill(4) + match.group(2),
                    date.get("when"),
                ),
            )

        # Record the sex of the person
        if self.data.get("fixed").get("gender") != "u":
            sex = etree.SubElement(element, "sex")
            sex.set("source", "VIAF")
            if self.data.get("fixed").get("gender") == "a":
                sex.text = "female"
            elif self.data.get("fixed").get("gender") == "b":
                sex.text = "male"

        # Create a list of links
        note = etree.SubElement(element, "note")
        note.set("type", "links")
        link_list = etree.SubElement(note, "list")
        link_list.set("type", "links")

        for sources in self.data.get("sources").get("source"):
            source_name, source_id = sources.get("#text").split("|")
            source_nsid = sources.get("@nsid")

            viaf_sources = {
                "BNF": {
                    "url": f"https://data.bnf.fr/en/{source_id}",
                    "title": "BNF",
                },
                "DNB": {"url": source_nsid, "title": "DNB"},
                "ISNI": {
                    "url": f"https://isni.org/isni/{source_nsid}",
                    "title": "ISNI",
                },
                "LC": {
                    "url": "https://id.loc.gov/authorities/names/"
                    + f"{source_nsid}",
                    "title": "LC",
                },
                "WKP": {
                    "url": f"https://wikidata.org/wiki/{source_nsid}",
                    "title": "Wikidata",
                },
            }

            if source_name in viaf_sources:
                item = etree.SubElement(link_list, "item")
                ref = etree.SubElement(item, "ref")
                ref.set("target", viaf_sources[source_name]["url"])
                title = etree.SubElement(ref, "title")
                title.text = viaf_sources[source_name]["title"]

        viaf_item = etree.SubElement(link_list, "item")
        viaf_ref = etree.SubElement(viaf_item, "ref")
        viaf_ref.set("target", f"https://viaf.org/viaf/{self.viaf_id}")
        viaf_title = etree.SubElement(viaf_ref, "title")
        viaf_title.text = "VIAF"

        # Sort the resulting list of links by title
        link_list[:] = sorted(link_list, key=lambda item: item[0][0].text)

        return element
