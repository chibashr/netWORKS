#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Variable Detector for ConfigMate Plugin

Intelligently detects template variables from device configurations.
Analyzes patterns, differences between devices, and common network configuration
elements to identify substitutable values.
"""

import re
import difflib
from typing import Dict, List, Any, Optional, Set, Tuple, Union
from loguru import logger
from collections import defaultdict, Counter
import time


class VariableCandidate:
    """Represents a potential template variable"""
    
    def __init__(self, name: str, pattern: str, description: str = "",
                 confidence: float = 0.0, examples: List[str] = None,
                 variable_type: str = "device"):
        self.name = name
        self.pattern = pattern
        self.description = description
        self.confidence = confidence
        self.examples = examples or []
        self.variable_type = variable_type  # "global" or "device"
        self.occurrences = []  # List of (line_number, matched_text) tuples
    
    def add_occurrence(self, line_number: int, matched_text: str):
        """Add an occurrence of this variable"""
        self.occurrences.append((line_number, matched_text))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'name': self.name,
            'pattern': self.pattern,
            'description': self.description,
            'confidence': self.confidence,
            'examples': self.examples,
            'variable_type': self.variable_type,
            'occurrence_count': len(self.occurrences)
        }


class VariableDetector:
    """
    Detects template variables from device configurations
    
    Provides functionality for:
    - Analyzing single device configurations for variable patterns
    - Comparing multiple device configurations to find differences
    - Pattern matching for common network configuration elements
    - Confidence scoring for variable candidates
    - Template generation with detected variables
    """
    
    def __init__(self):
        """Initialize the variable detector"""
        
        # Common network configuration patterns
        self.patterns = {
            'hostname': {
                'pattern': r'^hostname\s+(\S+)',
                'description': 'Device hostname',
                'confidence': 0.95,
                'variable_type': 'device'
            },
            'ip_address': {
                'pattern': r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b',
                'description': 'IP address',
                'confidence': 0.8,
                'variable_type': 'device'
            },
            'interface_name': {
                'pattern': r'^interface\s+(\S+)',
                'description': 'Interface name',
                'confidence': 0.9,
                'variable_type': 'device'
            },
            'vlan_id': {
                'pattern': r'\bvlan\s+(\d+)\b',
                'description': 'VLAN ID',
                'confidence': 0.85,
                'variable_type': 'device'
            },
            'subnet_mask': {
                'pattern': r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}',
                'description': 'Subnet mask',
                'confidence': 0.75,
                'variable_type': 'device'
            },
            'mac_address': {
                'pattern': r'\b([0-9a-fA-F]{4}\.[0-9a-fA-F]{4}\.[0-9a-fA-F]{4}|[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2})\b',
                'description': 'MAC address',
                'confidence': 0.9,
                'variable_type': 'device'
            },
            'description': {
                'pattern': r'description\s+(.+)',
                'description': 'Interface or device description',
                'confidence': 0.7,
                'variable_type': 'device'
            },
            'snmp_community': {
                'pattern': r'snmp-server community\s+(\S+)',
                'description': 'SNMP community string',
                'confidence': 0.8,
                'variable_type': 'global'
            },
            'ntp_server': {
                'pattern': r'ntp server\s+(\S+)',
                'description': 'NTP server address',
                'confidence': 0.85,
                'variable_type': 'global'
            },
            'dns_server': {
                'pattern': r'ip name-server\s+(\S+)',
                'description': 'DNS server address',
                'confidence': 0.85,
                'variable_type': 'global'
            },
            'domain_name': {
                'pattern': r'ip domain-name\s+(\S+)',
                'description': 'Domain name',
                'confidence': 0.9,
                'variable_type': 'global'
            },
            'banner': {
                'pattern': r'banner\s+\w+\s+(.+?)(?=banner|\n\S|\Z)',
                'description': 'Banner text',
                'confidence': 0.6,
                'variable_type': 'global'
            },
            'access_list_number': {
                'pattern': r'access-list\s+(\d+)',
                'description': 'Access list number',
                'confidence': 0.8,
                'variable_type': 'device'
            },
            'route_target': {
                'pattern': r'ip route\s+\S+\s+\S+\s+(\S+)',
                'description': 'Static route next hop',
                'confidence': 0.75,
                'variable_type': 'device'
            },
            'enable_password': {
                'pattern': r'enable password\s+(\S+)',
                'description': 'Enable password',
                'confidence': 0.9,
                'variable_type': 'global'
            },
            'enable_secret': {
                'pattern': r'enable secret\s+(\S+)',
                'description': 'Enable secret',
                'confidence': 0.9,
                'variable_type': 'global'
            },
            'timezone': {
                'pattern': r'clock timezone\s+(\S+)',
                'description': 'Timezone setting',
                'confidence': 0.8,
                'variable_type': 'global'
            },
            'contact': {
                'pattern': r'snmp-server contact\s+(.+)',
                'description': 'SNMP contact information',
                'confidence': 0.8,
                'variable_type': 'global'
            }
        }
        
        # Device-specific value patterns (values that likely differ between devices)
        self.device_specific_patterns = [
            r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',  # IP addresses
            r'\b[0-9a-fA-F]{4}\.[0-9a-fA-F]{4}\.[0-9a-fA-F]{4}\b',  # MAC addresses (Cisco format)
            r'\b[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}\b',  # MAC addresses (standard format)
            r'\b[A-Za-z][A-Za-z0-9\-_]{2,}\b',  # Hostnames and identifiers
        ]
        
        logger.info("VariableDetector initialized")
    
    def detect_variables_single_config(self, config_text: str, 
                                     device_name: str = "device") -> List[VariableCandidate]:
        """
        Detect variables in a single configuration
        
        Args:
            config_text: Configuration text to analyze
            device_name: Name of the device (for context)
            
        Returns:
            List of VariableCandidate objects
        """
        try:
            variables = []
            lines = config_text.splitlines()
            
            # Apply pattern matching
            for pattern_name, pattern_info in self.patterns.items():
                candidates = self._find_pattern_matches(
                    lines, pattern_name, pattern_info, device_name
                )
                variables.extend(candidates)
            
            # Look for device-specific values
            device_specific_vars = self._find_device_specific_values(lines, device_name)
            variables.extend(device_specific_vars)
            
            # Remove duplicates and sort by confidence
            variables = self._deduplicate_variables(variables)
            variables.sort(key=lambda x: x.confidence, reverse=True)
            
            logger.info(f"Detected {len(variables)} variable candidates in {device_name} configuration")
            return variables
            
        except Exception as e:
            logger.error(f"Error detecting variables in single config: {e}")
            return []
    
    def detect_variables_multi_config(self, config_dict: Dict[str, str]) -> List[VariableCandidate]:
        """
        Detect variables by comparing multiple device configurations
        
        Args:
            config_dict: Dictionary mapping device names to configuration text
            
        Returns:
            List of VariableCandidate objects with higher confidence
        """
        try:
            if len(config_dict) < 2:
                logger.warning("Need at least 2 configurations for multi-config analysis")
                return []
            
            variables = []
            device_names = list(config_dict.keys())
            
            # Find common configuration structure
            common_lines, diff_lines = self._find_config_differences(config_dict)
            
            # Analyze differences to find variable patterns
            for line_pattern in diff_lines:
                variable_candidates = self._analyze_line_differences(
                    line_pattern, config_dict
                )
                variables.extend(variable_candidates)
            
            # Cross-validate with single-config detection
            for device_name, config_text in config_dict.items():
                single_vars = self.detect_variables_single_config(config_text, device_name)
                variables.extend(single_vars)
            
            # Consolidate and score variables
            variables = self._consolidate_multi_config_variables(variables, config_dict)
            variables.sort(key=lambda x: x.confidence, reverse=True)
            
            logger.info(f"Detected {len(variables)} variable candidates from {len(config_dict)} configurations")
            return variables
            
        except Exception as e:
            logger.error(f"Error detecting variables in multi-config: {e}")
            return []
    
    def generate_template_from_config(self, config_text: str, 
                                    variables: List[VariableCandidate],
                                    device_name: str = "device") -> str:
        """
        Generate a template from configuration text using detected variables
        
        Args:
            config_text: Original configuration text
            variables: List of detected variables to substitute
            device_name: Device name for context
            
        Returns:
            Template text with variable substitutions
        """
        try:
            template = config_text
            substitutions_made = 0
            
            # Sort variables by specificity (longer patterns first)
            sorted_vars = sorted(variables, key=lambda x: len(x.pattern), reverse=True)
            
            for variable in sorted_vars:
                # Skip low-confidence variables
                if variable.confidence < 0.5:
                    continue
                
                # Create Jinja2 variable syntax
                jinja_var = f"{{{{ {variable.name} }}}}"
                
                # Apply substitution based on pattern
                try:
                    if variable.name in self.patterns:
                        # Use the defined pattern
                        pattern = self.patterns[variable.name]['pattern']
                        template, count = re.subn(pattern, 
                                                lambda m: m.group(0).replace(m.group(1), jinja_var),
                                                template)
                        substitutions_made += count
                    else:
                        # Use the variable's specific pattern
                        for line_num, matched_text in variable.occurrences:
                            template = template.replace(matched_text, jinja_var)
                            substitutions_made += 1
                
                except Exception as e:
                    logger.warning(f"Error substituting variable {variable.name}: {e}")
            
            # Add template header
            header = f"""# Configuration Template
# Generated from device: {device_name}
# Variables detected: {len([v for v in variables if v.confidence >= 0.5])}
# Substitutions made: {substitutions_made}
#
# Variables:
"""
            
            for variable in sorted_vars:
                if variable.confidence >= 0.5:
                    header += f"#   {variable.name}: {variable.description}\n"
            
            header += "#\n\n"
            
            template = header + template
            
            logger.info(f"Generated template with {substitutions_made} variable substitutions")
            return template
            
        except Exception as e:
            logger.error(f"Error generating template: {e}")
            return config_text
    
    def suggest_variable_values(self, variable_name: str, 
                              device_properties: Dict[str, Any]) -> List[str]:
        """
        Suggest values for a variable based on device properties
        
        Args:
            variable_name: Name of the variable
            device_properties: Device properties dictionary
            
        Returns:
            List of suggested values
        """
        suggestions = []
        
        try:
            # Map variable names to likely device properties
            property_mappings = {
                'hostname': ['name', 'hostname', 'device_name'],
                'ip_address': ['ip_address', 'management_ip', 'ip'],
                'mac_address': ['mac_address', 'mac'],
                'description': ['description', 'desc'],
                'location': ['location', 'site'],
                'domain_name': ['domain', 'domain_name'],
                'snmp_community': ['snmp_community', 'snmp_ro_community'],
                'vlan_id': ['vlan', 'vlan_id'],
                'interface_name': ['interface', 'mgmt_interface']
            }
            
            # Look for matching properties
            if variable_name in property_mappings:
                for prop_name in property_mappings[variable_name]:
                    value = device_properties.get(prop_name)
                    if value and str(value) not in suggestions:
                        suggestions.append(str(value))
            
            # Direct property name match
            if variable_name in device_properties:
                value = device_properties[variable_name]
                if value and str(value) not in suggestions:
                    suggestions.append(str(value))
            
            # Generate default values based on variable type
            if not suggestions:
                defaults = self._generate_default_values(variable_name)
                suggestions.extend(defaults)
                
        except Exception as e:
            logger.error(f"Error suggesting values for variable {variable_name}: {e}")
        
        return suggestions[:5]  # Return top 5 suggestions
    
    def _find_pattern_matches(self, lines: List[str], pattern_name: str,
                            pattern_info: Dict[str, Any], device_name: str) -> List[VariableCandidate]:
        """Find matches for a specific pattern in configuration lines"""
        candidates = []
        
        try:
            pattern = pattern_info['pattern']
            confidence = pattern_info['confidence']
            description = pattern_info['description']
            variable_type = pattern_info.get('variable_type', 'device')
            
            match_count = 0  # Track matches manually
            
            for line_num, line in enumerate(lines, 1):
                matches = list(re.finditer(pattern, line, re.IGNORECASE | re.MULTILINE))
                
                for match in matches:
                    if match.groups():
                        matched_value = match.group(1).strip()
                        if matched_value and len(matched_value) > 0:
                            match_count += 1
                            
                            # Create unique variable name
                            var_name = self._create_variable_name(pattern_name, matched_value, device_name)
                            
                            # Find existing candidate or create new one
                            existing_candidate = None
                            for candidate in candidates:
                                if candidate.name == var_name:
                                    existing_candidate = candidate
                                    break
                            
                            if existing_candidate:
                                existing_candidate.add_occurrence(line_num, matched_value)
                                # Update confidence based on occurrence count
                                occurrence_boost = min(len(existing_candidate.occurrences) * 0.05, 0.2)
                                existing_candidate.confidence = min(confidence + occurrence_boost, 1.0)
                            else:
                                candidate = VariableCandidate(
                                    name=var_name,
                                    pattern=pattern,
                                    description=description,
                                    confidence=confidence,
                                    examples=[matched_value],
                                    variable_type=variable_type
                                )
                                candidate.add_occurrence(line_num, matched_value)
                                candidates.append(candidate)
            
            logger.debug(f"Found {match_count} matches for pattern '{pattern_name}' in {device_name} config")
            
        except Exception as e:
            logger.error(f"Error finding pattern matches for {pattern_name}: {e}")
        
        return candidates
    
    def _find_device_specific_values(self, lines: List[str], 
                                   device_name: str) -> List[VariableCandidate]:
        """Find device-specific values that could be variables"""
        candidates = []
        
        try:
            # Look for repeated values that might be device-specific
            value_counts = Counter()
            value_lines = defaultdict(list)
            
            for line_num, line in enumerate(lines, 1):
                for pattern in self.device_specific_patterns:
                    matches = re.finditer(pattern, line)
                    for match in matches:
                        value = match.group(0)
                        value_counts[value] += 1
                        value_lines[value].append((line_num, line))
            
            # Create candidates for values that appear multiple times
            for value, count in value_counts.items():
                if count >= 2:  # Appears at least twice
                    var_name = self._generate_variable_name(value)
                    candidate = VariableCandidate(
                        name=var_name,
                        pattern=re.escape(value),
                        description=f"Device-specific value: {value}",
                        confidence=min(0.6 + (count * 0.1), 0.9),
                        examples=[value],
                        variable_type="device"
                    )
                    
                    for line_num, line in value_lines[value]:
                        candidate.add_occurrence(line_num, value)
                    
                    candidates.append(candidate)
                    
        except Exception as e:
            logger.error(f"Error finding device-specific values: {e}")
        
        return candidates
    
    def _find_config_differences(self, config_dict: Dict[str, str]) -> Tuple[List[str], List[str]]:
        """Find common lines and different lines across configurations"""
        try:
            all_lines = []
            device_lines = {}
            
            # Split all configurations into lines
            for device_name, config in config_dict.items():
                lines = config.splitlines()
                device_lines[device_name] = lines
                all_lines.extend(lines)
            
            # Find lines that appear in all configurations (common structure)
            line_counts = Counter(all_lines)
            total_devices = len(config_dict)
            
            common_lines = [line for line, count in line_counts.items() 
                          if count == total_devices]
            
            # Find line patterns that differ between devices
            diff_lines = []
            for line in set(all_lines):
                if line not in common_lines and line.strip():
                    diff_lines.append(line)
            
            return common_lines, diff_lines
            
        except Exception as e:
            logger.error(f"Error finding config differences: {e}")
            return [], []
    
    def _analyze_line_differences(self, line_pattern: str, 
                                config_dict: Dict[str, str]) -> List[VariableCandidate]:
        """Analyze a line pattern that differs between devices"""
        candidates = []
        
        try:
            # Find similar lines across devices
            similar_lines = defaultdict(list)
            
            for device_name, config in config_dict.items():
                lines = config.splitlines()
                for line_num, line in enumerate(lines, 1):
                    # Use basic similarity matching
                    similarity = difflib.SequenceMatcher(None, line_pattern, line).ratio()
                    if similarity > 0.7:  # 70% similarity threshold
                        similar_lines[device_name].append((line_num, line))
            
            if len(similar_lines) >= 2:
                # Find the differing parts
                line_texts = []
                for device_lines in similar_lines.values():
                    if device_lines:
                        line_texts.append(device_lines[0][1])  # Take first matching line
                
                if len(line_texts) >= 2:
                    diff_parts = self._find_line_differences(line_texts)
                    
                    for i, diff_part in enumerate(diff_parts):
                        var_name = f"variable_{len(candidates) + 1}"
                        candidate = VariableCandidate(
                            name=var_name,
                            pattern=re.escape(diff_part),
                            description=f"Detected variable from line differences",
                            confidence=0.7,
                            examples=line_texts,
                            variable_type="device"
                        )
                        candidates.append(candidate)
                        
        except Exception as e:
            logger.error(f"Error analyzing line differences: {e}")
        
        return candidates
    
    def _find_line_differences(self, lines: List[str]) -> List[str]:
        """Find the specific parts that differ between similar lines"""
        try:
            if len(lines) < 2:
                return []
            
            # Use difflib to find differences
            differ = difflib.Differ()
            diff = list(differ.compare(lines[0].split(), lines[1].split()))
            
            differences = []
            for item in diff:
                if item.startswith('- ') or item.startswith('+ '):
                    differences.append(item[2:])  # Remove prefix
            
            return differences
            
        except Exception as e:
            logger.error(f"Error finding line differences: {e}")
            return []
    
    def _consolidate_multi_config_variables(self, variables: List[VariableCandidate],
                                          config_dict: Dict[str, str]) -> List[VariableCandidate]:
        """Consolidate variables from multi-config analysis"""
        try:
            # Group variables by name
            var_groups = defaultdict(list)
            for var in variables:
                var_groups[var.name].append(var)
            
            consolidated = []
            
            for var_name, var_list in var_groups.items():
                if len(var_list) == 1:
                    consolidated.append(var_list[0])
                else:
                    # Merge variables with same name
                    merged_var = var_list[0]  # Start with first
                    
                    # Combine examples and occurrences
                    all_examples = set(merged_var.examples)
                    all_occurrences = merged_var.occurrences.copy()
                    
                    for var in var_list[1:]:
                        all_examples.update(var.examples)
                        all_occurrences.extend(var.occurrences)
                    
                    merged_var.examples = list(all_examples)
                    merged_var.occurrences = all_occurrences
                    
                    # Increase confidence for variables found in multiple configs
                    merged_var.confidence = min(merged_var.confidence * 1.2, 0.95)
                    
                    consolidated.append(merged_var)
            
            return consolidated
            
        except Exception as e:
            logger.error(f"Error consolidating variables: {e}")
            return variables
    
    def _deduplicate_variables(self, variables: List[VariableCandidate]) -> List[VariableCandidate]:
        """Remove duplicate variables"""
        try:
            seen_patterns = set()
            unique_vars = []
            
            for var in variables:
                # Use a combination of name and pattern as key
                key = f"{var.name}:{var.pattern}"
                if key not in seen_patterns:
                    seen_patterns.add(key)
                    unique_vars.append(var)
            
            return unique_vars
            
        except Exception as e:
            logger.error(f"Error deduplicating variables: {e}")
            return variables
    
    def _generate_variable_name(self, value: str) -> str:
        """Generate a meaningful variable name from a value"""
        try:
            # IP address
            if re.match(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', value):
                return "ip_address"
            
            # MAC address
            if re.match(r'[0-9a-fA-F]{4}\.[0-9a-fA-F]{4}\.[0-9a-fA-F]{4}', value):
                return "mac_address"
            
            # VLAN ID
            if value.isdigit() and 1 <= int(value) <= 4094:
                return "vlan_id"
            
            # Generic identifier
            if re.match(r'^[A-Za-z][A-Za-z0-9\-_]*$', value):
                return "identifier"
            
            return "variable"
            
        except Exception:
            return "variable"
    
    def _generate_default_values(self, variable_name: str) -> List[str]:
        """Generate default values for a variable type"""
        defaults = {
            'hostname': ['switch1', 'router1', 'device1'],
            'ip_address': ['192.168.1.1', '10.0.0.1', '172.16.0.1'],
            'mac_address': ['0000.1111.2222', '00:11:22:33:44:55'],
            'vlan_id': ['10', '20', '100'],
            'description': ['Management Interface', 'Uplink Port'],
            'domain_name': ['example.com', 'local.domain'],
            'snmp_community': ['public', 'readonly']
        }
        
        return defaults.get(variable_name, [f"<{variable_name}>"])

    def create_template_from_config(self, config_text: str, device, template_format: str = "text") -> str:
        """
        Create a template from device configuration
        
        Args:
            config_text: Original configuration text
            device: Device object containing device properties
            template_format: Format for template ("text" or "jinja2")
            
        Returns:
            Template text with variable substitutions or placeholders
        """
        try:
            device_name = device.get_property('name', 'Unknown Device')
            logger.info(f"Creating template from {device_name} configuration")
            
            # Detect variables in the configuration
            candidates = self.detect_variables_single_config(config_text, device_name)
            
            if template_format == "text":
                template_content = self._generate_text_template_from_config(config_text, candidates)
                
                # Separate variables by type
                global_variables = {}
                device_variables = {}
                
                for candidate in candidates:
                    if candidate.variable_type == "global":
                        global_variables[candidate.name] = candidate.examples[0] if candidate.examples else ""
                    else:
                        device_variables[candidate.name] = candidate.examples[0] if candidate.examples else ""
                
                # Store the separated variables for the calling code to use
                self._last_global_variables = global_variables
                self._last_device_variables = device_variables
                
                return template_content
            else:
                return self._generate_jinja_template_from_config(config_text, candidates)
            
        except Exception as e:
            logger.error(f"Error creating template from config: {e}")
            return config_text  # Return original if failed

    def _generate_text_template_from_config(self, config_text: str, 
                                          variables: List[VariableCandidate],
                                          device, device_name: str) -> str:
        """
        Generate a plain text template with placeholder comments
        
        Args:
            config_text: Original configuration text
            variables: List of detected variables to substitute  
            device: Device object for extracting values
            device_name: Device name for context
            
        Returns:
            Plain text template with comment placeholders for variables
        """
        try:
            template = config_text
            substitutions_made = 0
            device_properties = {}
            
            # Extract device properties
            if hasattr(device, 'properties'):
                device_properties = device.properties
            
            # Sort variables by confidence (highest first)
            sorted_vars = sorted(variables, key=lambda x: x.confidence, reverse=True)
            
            # Apply substitutions with placeholders
            for variable in sorted_vars:
                # Skip low-confidence variables
                if variable.confidence < 0.6:
                    continue
                
                # Get suggested value for this variable
                suggested_values = self.suggest_variable_values(variable.name, device_properties)
                suggested_value = suggested_values[0] if suggested_values else f"<{variable.name.upper()}>"
                
                # Create placeholder comment
                placeholder = f"<{variable.name.upper()}>"
                
                try:
                    # Apply substitution based on pattern
                    if variable.name in self.patterns:
                        # Use the defined pattern for replacement
                        pattern = self.patterns[variable.name]['pattern']
                        
                        def replace_match(match):
                            original = match.group(0)
                            replaced = original.replace(match.group(1), placeholder)
                            return replaced
                        
                        template, count = re.subn(pattern, replace_match, template)
                        substitutions_made += count
                    else:
                        # Use the variable's specific occurrences
                        for line_num, matched_text in variable.occurrences:
                            if matched_text in template:
                                template = template.replace(matched_text, placeholder)
                                substitutions_made += 1
                                
                except Exception as e:
                    logger.warning(f"Error substituting variable {variable.name}: {e}")
            
            # Add template header with variable information
            header = f"""! Configuration Template for {device_name}
! Generated from device configuration on {time.strftime('%Y-%m-%d %H:%M:%S')}
! Variables detected: {len([v for v in variables if v.confidence >= 0.6])}
! Substitutions made: {substitutions_made}
!
! Variables to customize:
"""
            
            for variable in sorted_vars:
                if variable.confidence >= 0.6:
                    suggested_values = self.suggest_variable_values(variable.name, device_properties)
                    example_value = suggested_values[0] if suggested_values else "value"
                    header += f"!   <{variable.name.upper()}>: {variable.description} (example: {example_value})\n"
            
            header += "!\n"
            
            template = header + template
            
            logger.info(f"Generated plain text template with {substitutions_made} variable substitutions")
            return template
            
        except Exception as e:
            logger.error(f"Error generating plain text template: {e}")
            return config_text

    def detect_variables_in_template(self, template_content: str) -> List[str]:
        """
        Detect variable placeholders in template content
        
        Args:
            template_content: Template content to analyze
            
        Returns:
            List of variable names found in the template
        """
        try:
            variable_names = []
            
            # Check for Jinja2 variables: {{ variable_name }}
            jinja_pattern = r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*[|\}]'
            jinja_matches = re.findall(jinja_pattern, template_content)
            variable_names.extend(jinja_matches)
            
            # Check for plain text placeholders: <VARIABLE_NAME>
            text_pattern = r'<([A-Z_][A-Z0-9_]*)>'
            text_matches = re.findall(text_pattern, template_content)
            # Convert to lowercase for consistency
            text_matches = [name.lower() for name in text_matches]
            variable_names.extend(text_matches)
            
            # Remove duplicates and return
            return list(set(variable_names))
            
        except Exception as e:
            logger.error(f"Error detecting variables in template: {e}")
            return []

    def _create_variable_name(self, pattern_name: str, matched_value: str, device_name: str) -> str:
        """
        Create a unique variable name based on pattern and matched value
        
        Args:
            pattern_name: Name of the pattern that matched
            matched_value: The actual matched value
            device_name: Name of the device
            
        Returns:
            Unique variable name
        """
        # For certain patterns, use generic names
        if pattern_name in ['hostname', 'domain_name', 'ntp_server', 'dns_server', 'snmp_community', 
                          'enable_password', 'enable_secret', 'timezone', 'contact', 'banner']:
            return pattern_name.upper()
        
        # For patterns that can have multiple instances, create unique names
        elif pattern_name in ['ip_address', 'interface_name', 'vlan_id', 'description']:
            # Create a simplified version of the matched value for naming
            simplified_value = re.sub(r'[^a-zA-Z0-9]', '_', matched_value).upper()
            return f"{pattern_name.upper()}_{simplified_value}"
        
        else:
            return pattern_name.upper() 