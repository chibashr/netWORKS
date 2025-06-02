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


class VariableCandidate:
    """Represents a potential template variable"""
    
    def __init__(self, name: str, pattern: str, description: str = "",
                 confidence: float = 0.0, examples: List[str] = None):
        self.name = name
        self.pattern = pattern
        self.description = description
        self.confidence = confidence
        self.examples = examples or []
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
                'confidence': 0.95
            },
            'ip_address': {
                'pattern': r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b',
                'description': 'IP address',
                'confidence': 0.8
            },
            'interface_name': {
                'pattern': r'^interface\s+(\S+)',
                'description': 'Interface name',
                'confidence': 0.9
            },
            'vlan_id': {
                'pattern': r'\bvlan\s+(\d+)\b',
                'description': 'VLAN ID',
                'confidence': 0.85
            },
            'subnet_mask': {
                'pattern': r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}',
                'description': 'Subnet mask',
                'confidence': 0.75
            },
            'mac_address': {
                'pattern': r'\b([0-9a-fA-F]{4}\.[0-9a-fA-F]{4}\.[0-9a-fA-F]{4}|[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2})\b',
                'description': 'MAC address',
                'confidence': 0.9
            },
            'description': {
                'pattern': r'description\s+(.+)',
                'description': 'Interface or device description',
                'confidence': 0.7
            },
            'snmp_community': {
                'pattern': r'snmp-server community\s+(\S+)',
                'description': 'SNMP community string',
                'confidence': 0.8
            },
            'ntp_server': {
                'pattern': r'ntp server\s+(\S+)',
                'description': 'NTP server address',
                'confidence': 0.85
            },
            'dns_server': {
                'pattern': r'ip name-server\s+(\S+)',
                'description': 'DNS server address',
                'confidence': 0.85
            },
            'domain_name': {
                'pattern': r'ip domain-name\s+(\S+)',
                'description': 'Domain name',
                'confidence': 0.9
            },
            'banner': {
                'pattern': r'banner\s+\w+\s+(.+?)(?=banner|\n\S|\Z)',
                'description': 'Banner text',
                'confidence': 0.6
            },
            'access_list_number': {
                'pattern': r'access-list\s+(\d+)',
                'description': 'Access list number',
                'confidence': 0.8
            },
            'route_target': {
                'pattern': r'ip route\s+\S+\s+\S+\s+(\S+)',
                'description': 'Static route next hop',
                'confidence': 0.75
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
            
            for line_num, line in enumerate(lines, 1):
                matches = re.finditer(pattern, line, re.IGNORECASE | re.MULTILINE)
                
                for match in matches:
                    if match.groups():
                        matched_value = match.group(1)
                        
                        # Create variable candidate
                        var_name = pattern_name
                        if pattern_name in ['ip_address', 'interface_name'] and len(matches) > 1:
                            var_name = f"{pattern_name}_{line_num}"
                        
                        candidate = VariableCandidate(
                            name=var_name,
                            pattern=pattern,
                            description=description,
                            confidence=confidence,
                            examples=[matched_value]
                        )
                        candidate.add_occurrence(line_num, matched_value)
                        candidates.append(candidate)
                        
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
                        examples=[value]
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
                            examples=line_texts
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