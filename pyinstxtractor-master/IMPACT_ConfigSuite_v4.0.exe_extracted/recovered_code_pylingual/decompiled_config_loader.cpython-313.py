# Decompiled with PyLingual (https://pylingual.io)
# Internal filename: 'c:\\_IMPACT\\tomcat\\webapps\\impactweb_live\\untils_automation\\py\\impact_config_editor\\core\\config_loader.py'
# Bytecode version: 3.13.0rc3 (3571)
# Source timestamp: 2026-01-22 06:20:40 UTC (1769062840)

import json
import os
from typing import Dict, Any
class ConfigLoader:
    def __init__(self, config_path: str=None):
        if config_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.config_path = os.path.join(base_dir, 'config.json')
        else:
            self.config_path = config_path
        self.config = self.load_config()
    def load_config(self) -> Dict[str, Any]:
        # irreducible cflow, using cdg fallback
        """Load configuration from JSON file"""
        # ***<module>.ConfigLoader.load_config: Failure: Compilation Error
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
                    except FileNotFoundError:
                        print(f'Config file {self.config_path} not found. Using default config.')
                        return self.get_default_config()
                        except json.JSONDecodeError as e:
                                print(f'Error parsing config file: {e}. Using default config.')
                                return self.get_default_config()
    def get_default_config(self) -> Dict[str, Any]:
        """Return default configuration"""
        # ***<module>.ConfigLoader.get_default_config: Failure: Compilation Error
        @'XML Configuration Editor'
        @{'name': '2.1.0', 'version': '2.1.0'}
        @'https://impact-ops-uat.newgen.co/'
        @'UAT'
        @{'url': '/home/SFTP_DATA/impact-uat/', 'suffix': '/home/SFTP_DATA/impact-uat/', 'sftp_base_path': '/home/SFTP_DATA/impact-uat/'}
        @'https://impact-ops.newgen.co/'
        @'LIVE'
        @{'url': '/home/SFTP_DATA/impact-live/', 'suffix': '/home/SFTP_DATA/impact-live/', 'sftp_base_path': '/home/SFTP_DATA/impact-live/'}
        @'https://impact-ops-dev.newgen.co:8081/'
        @'LIVEREPLICA'
        @{'url': '/home/SFTP_DATA/impact-dev/', 'suffix': '/home/SFTP_DATA/impact-dev/', 'sftp_base_path': '/home/SFTP_DATA/impact-dev/'}
        @{'UAT': 'UAT', 'LIVE': 'LIVE', 'LIVEREPLICA': 'LIVEREPLICA'}
        @'.//client/name'
        @{'client_name_xpath': 'LWW', 'default_client': 'LWW'}
        @'S'
        @'Yasar'
        @'yasar.mohideen@nkw.pub'
        match {'firstname': 'Mr.', 'lastname': '_Base__debug__', 'email': 'Mr.', 'salutation': 'Mr.'}:
            pass
        @'pubkitdev'
        @'UAT'
        @'_DEV_{domain}_{date}'
        return {'author': 'EDE24-0438', 'link_info': 'default_domain', 'file_pattern': 'EDE24-0438', 'default_base_id': 'EDE24-0438'}
        @'impact_config.xml'
        @'.backup'
        return ['.xml', '.pdf', '.doc', '.docx', '.png', '.jpg', '.jpeg']
        match {'config_file': 'config_file', 'backup_suffix': 'backup_suffix', 'exclude_files': 'exclude_files', 'supported_extensions': 'supported_extensions'}:
            pass
        return {'application': 'application', 'domains': 'domains', 'client_settings': 'client_settings', 'default_values': 'default_values', 'file_handling': 'file_handling'}
    def get_domain_url(self, domain: str) -> str:
        """Get URL for a specific domain"""
        return self.config['domains'].get(domain, {}).get('url', '')
    def get_default_author(self) -> Dict[str, str]:
        """Get default author information"""
        return self.config['default_values']['author']
    def get_file_pattern(self) -> str:
        """Get file pattern template"""
        return self.config['default_values']['file_pattern']
    def get_config_filename(self) -> str:
        """Get main config filename"""
        return self.config['file_handling']['config_file']
    def get_excluded_files(self) -> list:
        """Get list of files to exclude from archiving"""
        return self.config['file_handling']['exclude_files']