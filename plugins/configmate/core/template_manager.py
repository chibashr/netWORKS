#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Template Manager for ConfigMate Plugin

Handles creation, storage, and management of configuration templates.
Supports Jinja2 templating with variable substitution and metadata tracking.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from loguru import logger
import jinja2


class Template:
    """Represents a configuration template with metadata"""
    
    def __init__(self, name: str, content: str, platform: str = "generic", 
                 description: str = "", variables: Dict[str, Any] = None,
                 global_variables: Dict[str, Any] = None,
                 device_variables: Dict[str, Any] = None,
                 created_date: float = None, modified_date: float = None,
                 created_from_device: str = None):
        self.name = name
        self.content = content
        self.platform = platform
        self.description = description
        
        # Legacy support - if variables is provided but not global/device, split them
        if variables and not global_variables and not device_variables:
            self.global_variables, self.device_variables = self._categorize_variables(variables)
        else:
            self.global_variables = global_variables or {}
            self.device_variables = device_variables or {}
        
        # Keep legacy variables property for backward compatibility
        self.variables = {**self.global_variables, **self.device_variables}
        
        self.created_date = created_date or time.time()
        self.modified_date = modified_date or time.time()
        self.created_from_device = created_from_device
        
        # Jinja2 environment for rendering
        self._jinja_env = jinja2.Environment(
            undefined=jinja2.StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True
        )
    
    def _categorize_variables(self, variables: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Categorize variables into global and device-specific based on common patterns
        
        Args:
            variables: Dictionary of all variables
            
        Returns:
            Tuple of (global_variables, device_variables)
        """
        # Common global variable patterns
        global_patterns = {
            'password', 'passwd', 'secret', 'key', 'community', 'snmp_community',
            'domain', 'domain_name', 'dns_server', 'ntp_server', 'syslog_server',
            'timezone', 'contact', 'location_prefix', 'organization', 'company'
        }
        
        # Common device-specific patterns  
        device_patterns = {
            'hostname', 'name', 'device_name', 'ip_address', 'management_ip', 'mgmt_ip',
            'mac_address', 'interface', 'mgmt_interface', 'vlan_id', 'subnet_mask',
            'gateway', 'location', 'site', 'rack', 'position', 'serial_number'
        }
        
        global_vars = {}
        device_vars = {}
        
        for var_name, var_value in variables.items():
            var_lower = var_name.lower()
            
            # Check if it matches a global pattern
            if any(pattern in var_lower for pattern in global_patterns):
                global_vars[var_name] = var_value
            # Check if it matches a device pattern
            elif any(pattern in var_lower for pattern in device_patterns):
                device_vars[var_name] = var_value
            else:
                # Default to device-specific for unknown variables
                device_vars[var_name] = var_value
        
        return global_vars, device_vars
    
    def render(self, global_variables: Dict[str, Any] = None, 
               device_variables: Dict[str, Any] = None,
               variables: Dict[str, Any] = None) -> str:
        """
        Render the template with provided variables
        
        Args:
            global_variables: Global variables (apply to all devices)
            device_variables: Device-specific variables  
            variables: Legacy - all variables combined (for backward compatibility)
            
        Returns:
            Rendered configuration string
        """
        try:
            # Combine variables with precedence: device > global > template defaults
            render_vars = {}
            
            # Start with template defaults
            render_vars.update(self.global_variables)
            render_vars.update(self.device_variables)
            
            # Apply provided global variables
            if global_variables:
                render_vars.update(global_variables)
            
            # Apply provided device variables (highest precedence)
            if device_variables:
                render_vars.update(device_variables)
            
            # Legacy support - if variables provided, use them
            if variables:
                render_vars.update(variables)
            
            template = self._jinja_env.from_string(self.content)
            return template.render(**render_vars)
        except Exception as e:
            logger.error(f"Error rendering template '{self.name}': {e}")
            raise
    
    def validate_variables(self, variables: Dict[str, Any]) -> List[str]:
        """
        Validate that all required variables are provided
        
        Args:
            variables: Dictionary of variables to validate
            
        Returns:
            List of missing variable names
        """
        try:
            template = self._jinja_env.from_string(self.content)
            required_vars = set()
            
            # Parse template to find undefined variables
            try:
                template.render(**variables)
            except jinja2.UndefinedError as e:
                # Extract variable name from error message
                error_msg = str(e)
                if "is undefined" in error_msg:
                    var_name = error_msg.split("'")[1]
                    required_vars.add(var_name)
            
            return list(required_vars)
        except Exception as e:
            logger.error(f"Error validating template variables: {e}")
            return []
    
    def get_variables_from_content(self) -> List[str]:
        """
        Extract variable names from template content
        
        Returns:
            List of variable names found in the template
        """
        try:
            template = self._jinja_env.from_string(self.content)
            variables = set()
            
            # Parse the template AST to find variables
            ast = self._jinja_env.parse(self.content)
            for node in ast.find_all(jinja2.nodes.Name):
                if isinstance(node.ctx, jinja2.nodes.Load):
                    variables.add(node.name)
            
            # Remove Jinja2 built-ins
            builtin_vars = {'range', 'lipsum', 'dict', 'cycler', 'joiner', 'namespace'}
            variables = variables - builtin_vars
            
            return list(variables)
        except Exception as e:
            logger.error(f"Error extracting variables from template: {e}")
            return []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary for JSON serialization"""
        return {
            'name': self.name,
            'content': self.content,
            'platform': self.platform,
            'description': self.description,
            'variables': self.variables,  # Legacy field
            'global_variables': self.global_variables,
            'device_variables': self.device_variables,
            'created_date': self.created_date,
            'modified_date': self.modified_date,
            'created_from_device': self.created_from_device
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Template':
        """Create template from dictionary"""
        return cls(
            name=data.get('name', ''),
            content=data.get('content', ''),
            platform=data.get('platform', 'generic'),
            description=data.get('description', ''),
            variables=data.get('variables', {}),  # Legacy field
            global_variables=data.get('global_variables', {}),
            device_variables=data.get('device_variables', {}),
            created_date=data.get('created_date'),
            modified_date=data.get('modified_date'),
            created_from_device=data.get('created_from_device')
        )


class TemplateManager:
    """
    Manages configuration templates for ConfigMate plugin
    
    Provides functionality for:
    - Creating and editing templates
    - Storing templates with metadata
    - Loading and listing templates
    - Template validation and variable detection
    """
    
    def __init__(self, templates_path: Path):
        """
        Initialize the template manager
        
        Args:
            templates_path: Path where templates are stored
        """
        self.templates_path = Path(templates_path)
        self.templates_path.mkdir(parents=True, exist_ok=True)
        
        # In-memory template cache
        self._templates: Dict[str, Template] = {}
        
        # Load existing templates
        self._load_templates()
        
        logger.info(f"TemplateManager initialized with path: {self.templates_path}")
    
    def create_template(self, name: str, content: str, platform: str = "generic",
                       description: str = "", variables: Dict[str, Any] = None,
                       global_variables: Dict[str, Any] = None,
                       device_variables: Dict[str, Any] = None,
                       created_from_device: str = None) -> Template:
        """
        Create a new template
        
        Args:
            name: Template name
            content: Template content (Jinja2 format)
            platform: Target platform (cisco_ios, cisco_nxos, etc.)
            description: Template description
            variables: Default variable values (legacy - will be categorized)
            global_variables: Global variable values (apply to all devices)
            device_variables: Device-specific variable values
            created_from_device: Device ID if created from device config
            
        Returns:
            Created Template object
        """
        try:
            # Validate template name
            if not name or not isinstance(name, str):
                raise ValueError("Template name must be a non-empty string")
            
            # Check if template already exists
            if name in self._templates:
                raise ValueError(f"Template '{name}' already exists")
            
            # Create template
            template = Template(
                name=name,
                content=content,
                platform=platform,
                description=description,
                variables=variables,
                global_variables=global_variables,
                device_variables=device_variables,
                created_from_device=created_from_device
            )
            
            # Store in cache
            self._templates[name] = template
            
            # Save to disk
            self._save_template(template)
            
            logger.info(f"Created template: {name}")
            return template
            
        except Exception as e:
            logger.error(f"Failed to create template '{name}': {e}")
            raise
    
    def update_template(self, name: str, content: str = None, platform: str = None,
                       description: str = None, variables: Dict[str, Any] = None) -> Template:
        """
        Update an existing template
        
        Args:
            name: Template name
            content: New template content
            platform: New platform
            description: New description
            variables: New variable defaults
            
        Returns:
            Updated Template object
        """
        try:
            if name not in self._templates:
                raise ValueError(f"Template '{name}' not found")
            
            template = self._templates[name]
            
            # Update fields if provided
            if content is not None:
                template.content = content
            if platform is not None:
                template.platform = platform
            if description is not None:
                template.description = description
            if variables is not None:
                template.variables = variables
            
            # Update modification time
            template.modified_date = time.time()
            
            # Save to disk
            self._save_template(template)
            
            logger.info(f"Updated template: {name}")
            return template
            
        except Exception as e:
            logger.error(f"Failed to update template '{name}': {e}")
            raise
    
    def delete_template(self, name: str) -> bool:
        """
        Delete a template
        
        Args:
            name: Template name
            
        Returns:
            True if deleted successfully
        """
        try:
            if name not in self._templates:
                logger.warning(f"Template '{name}' not found for deletion")
                return False
            
            # Remove from cache
            del self._templates[name]
            
            # Delete file
            template_file = self.templates_path / f"{name}.json"
            if template_file.exists():
                template_file.unlink()
            
            logger.info(f"Deleted template: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete template '{name}': {e}")
            return False
    
    def get_template(self, name: str) -> Optional[Template]:
        """
        Get a template by name
        
        Args:
            name: Template name
            
        Returns:
            Template object or None if not found
        """
        return self._templates.get(name)
    
    def get_template_list(self) -> List[str]:
        """
        Get list of all template names
        
        Returns:
            List of template names
        """
        return list(self._templates.keys())
    
    def get_templates_by_platform(self, platform: str) -> List[Template]:
        """
        Get templates for a specific platform
        
        Args:
            platform: Platform name
            
        Returns:
            List of Template objects
        """
        return [template for template in self._templates.values() 
                if template.platform == platform]
    
    def search_templates(self, query: str) -> List[Template]:
        """
        Search templates by name or description
        
        Args:
            query: Search query
            
        Returns:
            List of matching Template objects
        """
        query_lower = query.lower()
        matches = []
        
        for template in self._templates.values():
            if (query_lower in template.name.lower() or 
                query_lower in template.description.lower()):
                matches.append(template)
        
        return matches
    
    def import_template_from_file(self, file_path: Path) -> Template:
        """
        Import a template from a JSON file
        
        Args:
            file_path: Path to template file
            
        Returns:
            Imported Template object
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            template = Template.from_dict(data)
            
            # Add to cache and save
            self._templates[template.name] = template
            self._save_template(template)
            
            logger.info(f"Imported template: {template.name}")
            return template
            
        except Exception as e:
            logger.error(f"Failed to import template from {file_path}: {e}")
            raise
    
    def export_template(self, name: str, file_path: Path) -> bool:
        """
        Export a template to a JSON file
        
        Args:
            name: Template name
            file_path: Export file path
            
        Returns:
            True if exported successfully
        """
        try:
            template = self.get_template(name)
            if not template:
                raise ValueError(f"Template '{name}' not found")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(template.to_dict(), f, indent=2, ensure_ascii=False)
            
            logger.info(f"Exported template '{name}' to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export template '{name}': {e}")
            return False
    
    def save_all(self):
        """Save all templates to disk"""
        try:
            for template in self._templates.values():
                self._save_template(template)
            logger.debug("Saved all templates to disk")
        except Exception as e:
            logger.error(f"Failed to save templates: {e}")
    
    def _load_templates(self):
        """Load templates from disk"""
        try:
            template_files = self.templates_path.glob("*.json")
            loaded_count = 0
            
            for template_file in template_files:
                try:
                    with open(template_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    template = Template.from_dict(data)
                    self._templates[template.name] = template
                    loaded_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to load template from {template_file}: {e}")
            
            logger.info(f"Loaded {loaded_count} templates from disk")
            
        except Exception as e:
            logger.error(f"Failed to load templates: {e}")
    
    def _save_template(self, template: Template):
        """Save a single template to disk"""
        try:
            template_file = self.templates_path / f"{template.name}.json"
            with open(template_file, 'w', encoding='utf-8') as f:
                json.dump(template.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save template '{template.name}': {e}")
            raise
    
    def get_template_info(self, name: str) -> Dict[str, Any]:
        """
        Get template information including statistics
        
        Args:
            name: Template name
            
        Returns:
            Dictionary with template information
        """
        template = self.get_template(name)
        if not template:
            return {}
        
        variables = template.get_variables_from_content()
        
        return {
            'name': template.name,
            'platform': template.platform,
            'description': template.description,
            'created_date': template.created_date,
            'modified_date': template.modified_date,
            'created_from_device': template.created_from_device,
            'variable_count': len(variables),
            'variables': variables,
            'content_lines': len(template.content.splitlines()),
            'content_size': len(template.content)
        } 