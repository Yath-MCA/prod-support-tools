import xml.etree.ElementTree as ET
import re
from datetime import datetime
from typing import Tuple, Optional
from .config_loader import ConfigLoader


class XMLProcessor:
    def __init__(self, config: ConfigLoader):
        self.config = config

    def extract_base_identifier(self, xml_content: str) -> str:
        """Extract base identifier from XML content"""
        try:
            root = ET.fromstring(xml_content)

            # Look for identifier or file-id elements
            identifier_elem = root.find(".//identifier[@type='doi']")
            file_id_elem = root.find(".//file-id")

            source_elem = identifier_elem if identifier_elem is not None else file_id_elem

            if source_elem is not None and source_elem.text:
                text = source_elem.text

                # Extract base identifier patterns
                patterns = [
                    r'^([A-Za-z]{3,}\d{2}-\d{4})',  # EDE24-0438 pattern
                    r'^([A-Za-z]+\d+-\d+)',  # Alternative pattern
                    r'^([A-Za-z0-9_-]+)'  # General pattern
                ]

                for pattern in patterns:
                    match = re.match(pattern, text)
                    if match:
                        base_id = match.group(1)
                        # Remove trailing underscores
                        if base_id.endswith('_'):
                            base_id = base_id[:-1]
                        return base_id

                # If no pattern matches, try to get the part before first underscore
                if '_' in text:
                    return text.split('_')[0]
                else:
                    return text

            return self.config.config["default_values"]["default_base_id"]

        except Exception as e:
            print(f"Error extracting base identifier: {e}")
            return self.config.config["default_values"]["default_base_id"]

    def generate_file_id(self, base_id: str, domain: str, optional_suffix: str = "") -> str:
        """Generate file ID based on pattern"""
        current_date = datetime.now().strftime("%d_%m_%y")
        pattern = self.config.get_file_pattern()

        file_id = f"{base_id}{pattern.format(domain=domain, date=current_date)}"

        if optional_suffix.strip():
            file_id += f"_{optional_suffix.strip()}"

        return file_id

    def update_contributor_info(self, root: ET.Element, contributor_data: dict) -> None:
        """Update multiple contributors' information in XML
        contributor_data: { 'role_name': { 'firstname': '...', ... }, ... }
        """
        for role, info in contributor_data.items():
            # Find the contributor with this exact role
            contributor = root.find(f".//contributor[@role='{role}']")
            
            if contributor is not None:
                self._update_existing_contributor(contributor, info)
            else:
                self._create_new_contributor(root, role, info)

    def _create_new_contributor(self, root: ET.Element, role: str, info: dict) -> None:
        """Create a new contributor element with a specific role following the sample structure"""
        contributor = ET.Element("contributor")
        contributor.set("role", role)
        contributor.set("task_id", "")
        contributor.set("abstract_task_id", "")

        # Consistent name format
        fn = info.get("firstname", "")
        ln = info.get("lastname", "")
        email = info.get("email", "")
        sal = info.get("salutation", "Mr.")
        full_name = f"{fn}.{ln}" if fn and ln else (fn or ln or "")

        # Sample structure: Only 'author' explicitly shows all 5 elements in user example,
        # but the request says "applicable for all". We will provide all for all roles to be safe,
        # or stick to name/email if that's preferred. The sample shows 'author' has all.
        # Let's ensure author always has all, and others have at least name/email.
        
        if role == "author":
            ET.SubElement(contributor, "salutation").text = sal
            ET.SubElement(contributor, "firstname").text = fn
            ET.SubElement(contributor, "lastname").text = ln
            
        ET.SubElement(contributor, "name").text = full_name
        ET.SubElement(contributor, "email").text = email

        root.append(contributor)

    def _update_existing_contributor(self, contributor: ET.Element, info: dict) -> None:
        """Update existing contributor element based on sample structure"""
        role = contributor.get("role")
        fn = info.get("firstname", "")
        ln = info.get("lastname", "")
        email = info.get("email", "")
        sal = info.get("salutation", "Mr.")
        full_name = f"{fn}.{ln}" if fn and ln else (fn or ln or "")
        
        # Ensure attributes are present
        if "task_id" not in contributor.attrib:
            contributor.set("task_id", "")
        if "abstract_task_id" not in contributor.attrib:
            contributor.set("abstract_task_id", "")

        # Find or create elements
        tags_needed = ["name", "email"]
        if role == "author":
            tags_needed = ["salutation", "firstname", "lastname"] + tags_needed
            
        # Clear existing to maintain order if necessary, or just update
        for tag in tags_needed:
            elem = contributor.find(tag)
            if elem is None:
                elem = ET.SubElement(contributor, tag)
            
            if tag == "firstname": elem.text = fn
            elif tag == "lastname": elem.text = ln
            elif tag == "name": elem.text = full_name
            elif tag == "email": elem.text = email
            elif tag == "salutation": elem.text = sal

    def update_link_info(self, root: ET.Element, link_info: str) -> None:
        """Update link-info element in XML"""
        link_elem = root.find(".//link-info")

        if link_elem is not None:
            link_elem.text = link_info
        else:
            link_elem = ET.Element("link-info")
            link_elem.text = link_info
            root.append(link_elem)

    def update_identifiers(self, root: ET.Element, file_id: str) -> None:
        """Update identifier and file-id elements in XML"""
        # Update identifier
        identifier = root.find(".//identifier[@type='doi']")
        if identifier is not None:
            identifier.text = file_id
        else:
            identifier = ET.Element("identifier")
            identifier.set("type", "doi")
            identifier.text = file_id
            root.append(identifier)

        # Update file-id
        file_id_elem = root.find(".//file-id")
        if file_id_elem is not None:
            file_id_elem.text = file_id
        else:
            file_id_elem = ET.Element("file-id")
            file_id_elem.text = file_id
            root.append(file_id_elem)

    def update_visual_editor_settings(self, root: ET.Element, mathlive_enabled: bool, mathtype_enabled: bool) -> None:
        """Update visual editor settings in XML"""
        settings_elem = root.find(".//visual-editor-settings")
        if settings_elem is None:
            settings_elem = ET.Element("visual-editor-settings")
            root.append(settings_elem)
        
        # Update or create MathLive
        ml_elem = settings_elem.find("mathlive")
        if ml_elem is None:
            ml_elem = ET.SubElement(settings_elem, "mathlive")
        ml_elem.text = "true" if mathlive_enabled else "false"
        
        # Update or create MathType
        mt_elem = settings_elem.find("mathtype")
        if mt_elem is None:
            mt_elem = ET.SubElement(settings_elem, "mathtype")
        mt_elem.text = "true" if mathtype_enabled else "false"
