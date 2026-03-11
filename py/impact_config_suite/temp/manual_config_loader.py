import json
import os
from typing import Dict, Any


class ConfigLoader:
    def __init__(self, config_path: str = None):
        if config_path is None:
            # Look for config.json in the same directory as this file's parent (the app root)
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.config_path = os.path.join(base_dir, "config.json")
        else:
            self.config_path = config_path
            
        self.config = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Config file {self.config_path} not found. Using default config.")
            return self.get_default_config()
        except json.JSONDecodeError as e:
            print(f"Error parsing config file: {e}. Using default config.")
            return self.get_default_config()

    def get_default_config(self) -> Dict[str, Any]:
        """Return default configuration"""
        return {
            "application": {
                "name": "XML Configuration Editor",
                "version": "2.1.0"
            },
            "domains": {
                "UAT": {
                    "url": "https://impact-ops-uat.newgen.co/", 
                    "suffix": "UAT",
                    "sftp_base_path": "/home/SFTP_DATA/impact-uat/"
                },
                "LIVE": {
                    "url": "https://impact-ops.newgen.co/", 
                    "suffix": "LIVE",
                    "sftp_base_path": "/home/SFTP_DATA/impact-live/"
                },
                "LIVEREPLICA": {
                    "url": "https://impact-ops-dev.newgen.co:8081/", 
                    "suffix": "LIVEREPLICA",
                    "sftp_base_path": "/home/SFTP_DATA/impact-dev/"
                }
            },
            "client_settings": {
                "client_name_xpath": ".//client/name",
                "default_client": "LWW"
            },
            "default_values": {
                "author": {
                    "firstname": "S",
                    "lastname": "Yasar",
                    "email": "yasar.mohideen@nkw.pub",
                    "salutation": "Mr."
                },
                "link_info": "pubkitdev",
                "default_domain": "UAT",
                "file_pattern": "_DEV_{domain}_{date}",
                "default_base_id": "EDE24-0438"
            },
            "file_handling": {
                "config_file": "impact_config.xml",
                "backup_suffix": ".backup",
                "exclude_files": ["impact_config.xml"],
                "supported_extensions": [".xml", ".pdf", ".doc", ".docx", ".png", ".jpg", ".jpeg"]
            }
        }

    def get_domain_url(self, domain: str) -> str:
        """Get URL for a specific domain"""
        return self.config["domains"].get(domain, {}).get("url", "")

    def get_default_author(self) -> Dict[str, str]:
        """Get default author information"""
        return self.config["default_values"]["author"]

    def get_file_pattern(self) -> str:
        """Get file pattern template"""
        return self.config["default_values"]["file_pattern"]

    def get_config_filename(self) -> str:
        """Get main config filename"""
        return self.config["file_handling"]["config_file"]

    def get_excluded_files(self) -> list:
        """Get list of files to exclude from archiving"""
        return self.config["file_handling"]["exclude_files"]
