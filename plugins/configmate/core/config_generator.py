#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configuration Generator for ConfigMate Plugin

Generates device configurations from templates using variable substitution
and device property mapping. Supports preview, validation, and batch operations.
"""

import re
from typing import Dict, List, Any, Optional, Union
from loguru import logger

# Import TemplateManager - try absolute import first
try:
    from configmate.core.template_manager import TemplateManager, Template
except ImportError:
    # Fallback to relative path
    import sys
    import os
    plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, plugin_dir)
    from core.template_manager import TemplateManager, Template


class ConfigGenerator:
    """
    Generates device configurations from templates
    
    Provides functionality for:
    - Generating configurations with variable substitution
    - Mapping device properties to template variables
    - Validating generated configurations
    - Preview generation without saving
    - Batch configuration generation
    """
    
    def __init__(self, template_manager: TemplateManager):
        """
        Initialize the configuration generator
        
        Args:
            template_manager: TemplateManager instance for accessing templates
        """
        self.template_manager = template_manager
        
        # Default property mappings for common variables
        self.default_mappings = {
            'hostname': ['name', 'hostname', 'device_name'],
            'ip_address': ['ip_address', 'ip', 'management_ip'],
            'mac_address': ['mac_address', 'mac'],
            'description': ['description', 'desc'],
            'location': ['location', 'site'],
            'contact': ['contact', 'owner'],
            'domain': ['domain', 'domain_name'],
            'vlan': ['vlan', 'vlan_id'],
            'interface': ['interface', 'mgmt_interface'],
            'gateway': ['gateway', 'default_gateway'],
            'dns_server': ['dns_server', 'dns1', 'primary_dns'],
            'ntp_server': ['ntp_server', 'ntp1', 'primary_ntp'],
            'snmp_community': ['snmp_community', 'snmp_ro_community']
        }
        
        logger.info("ConfigGenerator initialized")
    
    def generate_config(self, device: Any, template_name: str,
                       custom_variables: Dict[str, Any] = None,
                       preview_only: bool = False) -> Optional[str]:
        """
        Generate configuration for a device using a template
        
        Args:
            device: Device object with properties
            template_name: Name of template to use
            custom_variables: Custom variables to override defaults
            preview_only: If True, don't save generated config
            
        Returns:
            Generated configuration string or None if failed
        """
        try:
            # Get template
            template = self.template_manager.get_template(template_name)
            if not template:
                raise ValueError(f"Template '{template_name}' not found")
            
            # Extract variables from device properties
            variables = self._extract_device_variables(device, template)
            
            # Override with custom variables if provided
            if custom_variables:
                variables.update(custom_variables)
            
            # Validate required variables
            missing_vars = template.validate_variables(variables)
            if missing_vars:
                logger.warning(f"Missing variables for template '{template_name}': {missing_vars}")
                # Use default values or empty strings for missing variables
                for var in missing_vars:
                    if var not in variables:
                        variables[var] = template.variables.get(var, f"{{{{ {var} }}}}")
            
            # Render template
            config = template.render(variables)
            
            # Post-process configuration
            config = self._post_process_config(config, device)
            
            # Save generated config if not preview only
            if not preview_only:
                self._save_generated_config(device, template_name, config, variables)
            
            logger.info(f"Generated config for device '{device.get_property('name', 'Unknown')}' using template '{template_name}'")
            return config
            
        except Exception as e:
            logger.error(f"Failed to generate config for device '{device.get_property('name', 'Unknown')}': {e}")
            return None
    
    def generate_configs_batch(self, devices: List[Any], template_name: str,
                             custom_variables: Dict[str, Any] = None) -> Dict[str, str]:
        """
        Generate configurations for multiple devices
        
        Args:
            devices: List of device objects
            template_name: Name of template to use
            custom_variables: Custom variables to apply to all devices
            
        Returns:
            Dictionary mapping device IDs to generated configurations
        """
        results = {}
        
        try:
            template = self.template_manager.get_template(template_name)
            if not template:
                raise ValueError(f"Template '{template_name}' not found")
            
            for device in devices:
                try:
                    config = self.generate_config(device, template_name, custom_variables)
                    if config:
                        results[device.device_id] = config
                except Exception as e:
                    logger.error(f"Failed to generate config for device {device.get_property('name')}: {e}")
                    results[device.device_id] = None
            
            logger.info(f"Generated {len([r for r in results.values() if r])} configs out of {len(devices)} devices")
            
        except Exception as e:
            logger.error(f"Batch config generation failed: {e}")
        
        return results
    
    def preview_config(self, device: Any, template_name: str,
                      custom_variables: Dict[str, Any] = None) -> Optional[str]:
        """
        Preview configuration without saving
        
        Args:
            device: Device object
            template_name: Name of template to use
            custom_variables: Custom variables to use
            
        Returns:
            Preview configuration string
        """
        return self.generate_config(device, template_name, custom_variables, preview_only=True)
    
    def get_template_variables_for_device(self, device: Any, template_name: str) -> Dict[str, Any]:
        """
        Get variables that would be used for a device with a template
        
        Args:
            device: Device object
            template_name: Name of template
            
        Returns:
            Dictionary of variables and their values
        """
        try:
            template = self.template_manager.get_template(template_name)
            if not template:
                return {}
            
            variables = self._extract_device_variables(device, template)
            
            # Add template default variables
            for var_name, default_value in template.variables.items():
                if var_name not in variables:
                    variables[var_name] = default_value
            
            return variables
            
        except Exception as e:
            logger.error(f"Failed to get template variables: {e}")
            return {}
    
    def validate_config_syntax(self, config: str, platform: str = "cisco_ios") -> List[str]:
        """
        Validate generated configuration syntax
        
        Args:
            config: Configuration string to validate
            platform: Platform type for validation rules
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        try:
            lines = config.splitlines()
            
            if platform.startswith("cisco"):
                errors.extend(self._validate_cisco_syntax(lines))
            elif platform.startswith("juniper"):
                errors.extend(self._validate_juniper_syntax(lines))
            else:
                # Generic validation
                errors.extend(self._validate_generic_syntax(lines))
                
        except Exception as e:
            logger.error(f"Error validating config syntax: {e}")
            errors.append(f"Validation error: {e}")
        
        return errors
    
    def _extract_device_variables(self, device: Any, template: Template) -> Dict[str, Any]:
        """
        Extract variables from device properties
        
        Args:
            device: Device object
            template: Template object
            
        Returns:
            Dictionary of extracted variables
        """
        variables = {}
        
        try:
            # Get template variables to know what we need
            template_vars = template.get_variables_from_content()
            
            # Map device properties to template variables
            for var_name in template_vars:
                value = self._get_device_property_for_variable(device, var_name)
                if value is not None:
                    variables[var_name] = value
            
            # Add common derived variables
            variables.update(self._get_derived_variables(device, variables))
            
        except Exception as e:
            logger.error(f"Error extracting device variables: {e}")
        
        return variables
    
    def _get_device_property_for_variable(self, device: Any, var_name: str) -> Any:
        """
        Get device property value for a template variable
        
        Args:
            device: Device object
            var_name: Variable name
            
        Returns:
            Property value or None if not found
        """
        try:
            # First try direct property name match
            value = device.get_property(var_name)
            if value is not None:
                return value
            
            # Try mapped property names
            if var_name in self.default_mappings:
                for prop_name in self.default_mappings[var_name]:
                    value = device.get_property(prop_name)
                    if value is not None:
                        return value
            
            # Try case-insensitive search
            for prop_name, prop_value in device.properties.items():
                if prop_name.lower() == var_name.lower():
                    return prop_value
            
            return None
            
        except Exception as e:
            logger.debug(f"Error getting device property for variable '{var_name}': {e}")
            return None
    
    def _get_derived_variables(self, device: Any, variables: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate derived variables from device properties
        
        Args:
            device: Device object
            variables: Existing variables
            
        Returns:
            Dictionary of derived variables
        """
        derived = {}
        
        try:
            # Hostname variations
            hostname = variables.get('hostname') or device.get_property('name', '')
            if hostname:
                derived['hostname_upper'] = hostname.upper()
                derived['hostname_lower'] = hostname.lower()
                derived['hostname_clean'] = re.sub(r'[^a-zA-Z0-9\-]', '', hostname)
            
            # IP address variations
            ip_address = variables.get('ip_address') or device.get_property('ip_address', '')
            if ip_address:
                derived['ip_octets'] = ip_address.split('.')
                derived['network'] = '.'.join(ip_address.split('.')[:-1]) + '.0'
                
                # Calculate common subnets
                octets = ip_address.split('.')
                if len(octets) == 4:
                    derived['class_c_network'] = f"{octets[0]}.{octets[1]}.{octets[2]}.0"
                    derived['host_part'] = octets[3]
            
            # MAC address variations
            mac = variables.get('mac_address') or device.get_property('mac_address', '')
            if mac:
                # Remove separators and normalize
                clean_mac = re.sub(r'[:-]', '', mac).upper()
                derived['mac_clean'] = clean_mac
                derived['mac_cisco'] = ':'.join([clean_mac[i:i+2] for i in range(0, 12, 2)])
                derived['mac_dash'] = '-'.join([clean_mac[i:i+2] for i in range(0, 12, 2)])
            
            # VLAN-related variables
            vlan = variables.get('vlan')
            if vlan:
                derived['vlan_name'] = f"VLAN_{vlan}"
                derived['vlan_description'] = f"VLAN {vlan} - {hostname}" if hostname else f"VLAN {vlan}"
            
            # Interface naming
            interface = variables.get('interface')
            if interface:
                # Normalize interface names
                if 'ethernet' in interface.lower():
                    derived['interface_short'] = interface.replace('Ethernet', 'Eth').replace('ethernet', 'eth')
                elif 'gigabit' in interface.lower():
                    derived['interface_short'] = interface.replace('GigabitEthernet', 'Gi').replace('gigabitethernet', 'gi')
            
            # Time-based variables
            import datetime
            now = datetime.datetime.now()
            derived['current_date'] = now.strftime('%Y-%m-%d')
            derived['current_time'] = now.strftime('%H:%M:%S')
            derived['current_year'] = str(now.year)
            
        except Exception as e:
            logger.error(f"Error generating derived variables: {e}")
        
        return derived
    
    def _post_process_config(self, config: str, device: Any) -> str:
        """
        Post-process generated configuration
        
        Args:
            config: Generated configuration
            device: Device object
            
        Returns:
            Post-processed configuration
        """
        try:
            # Remove empty lines at start and end
            config = config.strip()
            
            # Ensure consistent line endings
            config = config.replace('\r\n', '\n').replace('\r', '\n')
            
            # Remove excessive blank lines
            config = re.sub(r'\n\s*\n\s*\n', '\n\n', config)
            
            # Add header comment
            device_name = device.get_property('name', 'Unknown Device')
            header = f"!\n! Configuration generated by ConfigMate\n! Device: {device_name}\n! Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n!\n"
            config = header + config
            
            return config
            
        except Exception as e:
            logger.error(f"Error post-processing config: {e}")
            return config
    
    def _save_generated_config(self, device: Any, template_name: str, 
                             config: str, variables: Dict[str, Any]):
        """
        Save generated configuration and metadata
        
        Args:
            device: Device object
            template_name: Template name used
            config: Generated configuration
            variables: Variables used for generation
        """
        try:
            # This would save to the data directory
            # Implementation depends on plugin data storage structure
            device_id = device.device_id
            logger.debug(f"Saved generated config for device {device_id}")
            
        except Exception as e:
            logger.error(f"Error saving generated config: {e}")
    
    def _validate_cisco_syntax(self, lines: List[str]) -> List[str]:
        """Validate Cisco configuration syntax"""
        errors = []
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('!'):
                continue
            
            # Check for common syntax errors
            if line.startswith(' ') and not any(line.startswith(prefix) for prefix in [' description', ' ip address', ' switchport']):
                if i > 1 and not lines[i-2].strip().endswith(':'):
                    errors.append(f"Line {i}: Unexpected indentation")
            
            # Check for incomplete commands
            if line.endswith('\\'):
                errors.append(f"Line {i}: Incomplete command")
        
        return errors
    
    def _validate_juniper_syntax(self, lines: List[str]) -> List[str]:
        """Validate Juniper configuration syntax"""
        errors = []
        brace_count = 0
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            brace_count += line.count('{') - line.count('}')
            
            # Check for unmatched braces
            if brace_count < 0:
                errors.append(f"Line {i}: Unmatched closing brace")
        
        if brace_count > 0:
            errors.append("Configuration has unmatched opening braces")
        
        return errors
    
    def _validate_generic_syntax(self, lines: List[str]) -> List[str]:
        """Generic configuration validation"""
        errors = []
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            
            # Check for suspicious patterns
            if '{{' in line and '}}' in line:
                errors.append(f"Line {i}: Unresolved template variable")
            
            if line.endswith('\\'):
                errors.append(f"Line {i}: Line continuation not supported")
        
        return errors


import datetime 