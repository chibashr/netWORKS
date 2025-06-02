#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configuration Comparator for ConfigMate Plugin

Provides side-by-side configuration comparison with diff highlighting.
Supports comparing device configurations, show command outputs, and templates.
"""

import difflib
import re
from typing import Dict, List, Any, Optional, Tuple, Union
from loguru import logger
from enum import Enum


class ComparisonType(Enum):
    """Types of configuration comparisons"""
    CONFIGURATION = "configuration"
    SHOW_COMMAND = "show_command"
    TEMPLATE = "template"


class DiffType(Enum):
    """Types of differences found"""
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    CONTEXT = "context"


class ComparisonResult:
    """Represents the result of a configuration comparison"""
    
    def __init__(self, device1_name: str, device2_name: str, 
                 device1_config: str, device2_config: str,
                 comparison_type: ComparisonType = ComparisonType.CONFIGURATION):
        self.device1_name = device1_name
        self.device2_name = device2_name
        self.device1_config = device1_config
        self.device2_config = device2_config
        self.comparison_type = comparison_type
        
        # Comparison results
        self.unified_diff = []
        self.side_by_side_diff = []
        self.statistics = {}
        self.differences = []
        
        # Perform comparison
        self._perform_comparison()
    
    def _perform_comparison(self):
        """Perform the actual comparison"""
        try:
            lines1 = self.device1_config.splitlines(keepends=False)
            lines2 = self.device2_config.splitlines(keepends=False)
            
            # Generate unified diff
            self.unified_diff = list(difflib.unified_diff(
                lines1, lines2,
                fromfile=self.device1_name,
                tofile=self.device2_name,
                lineterm=''
            ))
            
            # Generate side-by-side diff
            self.side_by_side_diff = list(difflib.context_diff(
                lines1, lines2,
                fromfile=self.device1_name,
                tofile=self.device2_name,
                lineterm=''
            ))
            
            # Calculate statistics
            self._calculate_statistics(lines1, lines2)
            
            # Extract structured differences
            self._extract_differences(lines1, lines2)
            
        except Exception as e:
            logger.error(f"Error performing configuration comparison: {e}")
    
    def _calculate_statistics(self, lines1: List[str], lines2: List[str]):
        """Calculate comparison statistics"""
        try:
            differ = difflib.Differ()
            diff = list(differ.compare(lines1, lines2))
            
            added = len([line for line in diff if line.startswith('+ ')])
            removed = len([line for line in diff if line.startswith('- ')])
            unchanged = len([line for line in diff if line.startswith('  ')])
            
            total_lines1 = len(lines1)
            total_lines2 = len(lines2)
            
            self.statistics = {
                'lines_added': added,
                'lines_removed': removed,
                'lines_unchanged': unchanged,
                'total_lines_device1': total_lines1,
                'total_lines_device2': total_lines2,
                'similarity_ratio': difflib.SequenceMatcher(None, lines1, lines2).ratio(),
                'difference_count': added + removed
            }
            
        except Exception as e:
            logger.error(f"Error calculating statistics: {e}")
            self.statistics = {}
    
    def _extract_differences(self, lines1: List[str], lines2: List[str]):
        """Extract structured differences"""
        try:
            differ = difflib.Differ()
            diff = list(differ.compare(lines1, lines2))
            
            current_section = None
            line_num1 = 0
            line_num2 = 0
            
            for line in diff:
                if line.startswith('  '):  # Unchanged line
                    line_num1 += 1
                    line_num2 += 1
                elif line.startswith('- '):  # Removed line
                    self.differences.append({
                        'type': DiffType.REMOVED,
                        'device1_line': line_num1 + 1,
                        'device2_line': None,
                        'content': line[2:],
                        'section': self._get_config_section(line[2:])
                    })
                    line_num1 += 1
                elif line.startswith('+ '):  # Added line
                    self.differences.append({
                        'type': DiffType.ADDED,
                        'device1_line': None,
                        'device2_line': line_num2 + 1,
                        'content': line[2:],
                        'section': self._get_config_section(line[2:])
                    })
                    line_num2 += 1
                    
        except Exception as e:
            logger.error(f"Error extracting differences: {e}")
    
    def _get_config_section(self, line: str) -> str:
        """Determine which configuration section a line belongs to"""
        line = line.strip()
        
        # Cisco IOS sections
        if line.startswith('interface '):
            return f"Interface: {line[10:]}"
        elif line.startswith('router '):
            return f"Routing: {line[7:]}"
        elif line.startswith('ip route'):
            return "Static Routes"
        elif line.startswith('access-list'):
            return "Access Lists"
        elif line.startswith('vlan'):
            return "VLANs"
        elif line.startswith('hostname'):
            return "System"
        elif line.startswith('snmp'):
            return "SNMP"
        elif line.startswith('ntp'):
            return "NTP"
        elif line.startswith('logging'):
            return "Logging"
        else:
            return "Global"
    
    def get_html_diff(self) -> str:
        """Generate HTML representation of the diff"""
        try:
            html_diff = difflib.HtmlDiff()
            return html_diff.make_file(
                self.device1_config.splitlines(),
                self.device2_config.splitlines(),
                fromdesc=self.device1_name,
                todesc=self.device2_name,
                context=True,
                numlines=3
            )
        except Exception as e:
            logger.error(f"Error generating HTML diff: {e}")
            return ""
    
    def export_to_text(self, file_path: str) -> bool:
        """Export comparison results to text file"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"Configuration Comparison Report\n")
                f.write(f"{'=' * 50}\n\n")
                f.write(f"Device 1: {self.device1_name}\n")
                f.write(f"Device 2: {self.device2_name}\n")
                f.write(f"Comparison Type: {self.comparison_type.value}\n\n")
                
                # Statistics
                f.write("Statistics:\n")
                f.write(f"  Lines Added: {self.statistics.get('lines_added', 0)}\n")
                f.write(f"  Lines Removed: {self.statistics.get('lines_removed', 0)}\n")
                f.write(f"  Lines Unchanged: {self.statistics.get('lines_unchanged', 0)}\n")
                f.write(f"  Similarity: {self.statistics.get('similarity_ratio', 0):.2%}\n\n")
                
                # Unified diff
                f.write("Unified Diff:\n")
                f.write("-" * 30 + "\n")
                for line in self.unified_diff:
                    f.write(line + '\n')
                
            return True
            
        except Exception as e:
            logger.error(f"Error exporting comparison to {file_path}: {e}")
            return False


class ConfigComparator:
    """
    Compares device configurations and show command outputs
    
    Provides functionality for:
    - Side-by-side configuration comparison
    - Highlighting differences with color coding
    - Filtering and ignoring irrelevant differences
    - Exporting comparison results
    - Comparing multiple devices at once
    """
    
    def __init__(self):
        """Initialize the configuration comparator"""
        
        # Default ignore patterns for Cisco configurations
        self.default_ignore_patterns = [
            r'^! Last configuration change.*',
            r'^! NVRAM config last updated.*',
            r'^! No configuration change since last restart',
            r'^!Time:.*',
            r'^ntp clock-period \d+',
            r'^crypto key generate rsa general-keys modulus \d+',
            r'^! version \d+\.\d+',
            r'^Building configuration...',
            r'^Current configuration : \d+ bytes'
        ]
        
        # Ignore patterns (can be customized)
        self.ignore_patterns = self.default_ignore_patterns.copy()
        
        logger.info("ConfigComparator initialized")
    
    def compare_devices(self, device1: Any, device2: Any, 
                       command: str = "show running-config",
                       ignore_timestamps: bool = True,
                       ignore_comments: bool = True,
                       context_lines: int = 3) -> ComparisonResult:
        """
        Compare configurations between two devices
        
        Args:
            device1: First device object
            device2: Second device object
            command: Command to compare (e.g., "show running-config")
            ignore_timestamps: Whether to ignore timestamp differences
            ignore_comments: Whether to ignore comment lines
            context_lines: Number of context lines to show
            
        Returns:
            ComparisonResult object
        """
        try:
            # Get configurations from devices
            config1 = self._get_device_config(device1, command)
            config2 = self._get_device_config(device2, command)
            
            if not config1:
                logger.warning(f"No configuration found for device {device1.get_property('name')}")
                config1 = ""
            
            if not config2:
                logger.warning(f"No configuration found for device {device2.get_property('name')}")
                config2 = ""
            
            # Preprocess configurations
            if ignore_timestamps or ignore_comments:
                config1 = self._preprocess_config(config1, ignore_timestamps, ignore_comments)
                config2 = self._preprocess_config(config2, ignore_timestamps, ignore_comments)
            
            # Create comparison result
            result = ComparisonResult(
                device1.get_property('name', 'Device 1'),
                device2.get_property('name', 'Device 2'),
                config1,
                config2,
                ComparisonType.CONFIGURATION
            )
            
            logger.info(f"Compared configurations between {result.device1_name} and {result.device2_name}")
            return result
            
        except Exception as e:
            logger.error(f"Error comparing device configurations: {e}")
            # Return empty comparison result
            return ComparisonResult("Error", "Error", "", "", ComparisonType.CONFIGURATION)
    
    def compare_show_commands(self, device1: Any, device2: Any, 
                            command: str,
                            ignore_timestamps: bool = True) -> ComparisonResult:
        """
        Compare show command outputs between two devices
        
        Args:
            device1: First device object
            device2: Second device object
            command: Show command to compare
            ignore_timestamps: Whether to ignore timestamp differences
            
        Returns:
            ComparisonResult object
        """
        try:
            # Get command outputs
            output1 = self._get_command_output(device1, command)
            output2 = self._get_command_output(device2, command)
            
            if not output1:
                logger.warning(f"No output found for command '{command}' on device {device1.get_property('name')}")
                output1 = ""
            
            if not output2:
                logger.warning(f"No output found for command '{command}' on device {device2.get_property('name')}")
                output2 = ""
            
            # Preprocess outputs
            if ignore_timestamps:
                output1 = self._preprocess_show_output(output1)
                output2 = self._preprocess_show_output(output2)
            
            # Create comparison result
            result = ComparisonResult(
                f"{device1.get_property('name', 'Device 1')} ({command})",
                f"{device2.get_property('name', 'Device 2')} ({command})",
                output1,
                output2,
                ComparisonType.SHOW_COMMAND
            )
            
            logger.info(f"Compared '{command}' output between {device1.get_property('name')} and {device2.get_property('name')}")
            return result
            
        except Exception as e:
            logger.error(f"Error comparing show command outputs: {e}")
            return ComparisonResult("Error", "Error", "", "", ComparisonType.SHOW_COMMAND)
    
    def compare_multiple_devices(self, devices: List[Any], 
                               command: str = "show running-config") -> List[ComparisonResult]:
        """
        Compare configurations across multiple devices
        
        Args:
            devices: List of device objects
            command: Command to compare
            
        Returns:
            List of ComparisonResult objects for all pairs
        """
        results = []
        
        try:
            if len(devices) < 2:
                logger.warning("Need at least 2 devices for comparison")
                return results
            
            # Compare each pair of devices
            for i in range(len(devices)):
                for j in range(i + 1, len(devices)):
                    result = self.compare_devices(devices[i], devices[j], command)
                    results.append(result)
            
            logger.info(f"Performed {len(results)} pairwise comparisons")
            
        except Exception as e:
            logger.error(f"Error in multiple device comparison: {e}")
        
        return results
    
    def compare_templates(self, template1_content: str, template2_content: str,
                         template1_name: str = "Template 1", 
                         template2_name: str = "Template 2") -> ComparisonResult:
        """
        Compare two configuration templates
        
        Args:
            template1_content: Content of first template
            template2_content: Content of second template
            template1_name: Name of first template
            template2_name: Name of second template
            
        Returns:
            ComparisonResult object
        """
        try:
            result = ComparisonResult(
                template1_name,
                template2_name,
                template1_content,
                template2_content,
                ComparisonType.TEMPLATE
            )
            
            logger.info(f"Compared templates '{template1_name}' and '{template2_name}'")
            return result
            
        except Exception as e:
            logger.error(f"Error comparing templates: {e}")
            return ComparisonResult("Error", "Error", "", "", ComparisonType.TEMPLATE)
    
    def add_ignore_pattern(self, pattern: str):
        """
        Add a regex pattern to ignore during comparisons
        
        Args:
            pattern: Regular expression pattern to ignore
        """
        if pattern not in self.ignore_patterns:
            self.ignore_patterns.append(pattern)
            logger.debug(f"Added ignore pattern: {pattern}")
    
    def remove_ignore_pattern(self, pattern: str):
        """
        Remove an ignore pattern
        
        Args:
            pattern: Pattern to remove
        """
        if pattern in self.ignore_patterns:
            self.ignore_patterns.remove(pattern)
            logger.debug(f"Removed ignore pattern: {pattern}")
    
    def reset_ignore_patterns(self):
        """Reset ignore patterns to defaults"""
        self.ignore_patterns = self.default_ignore_patterns.copy()
        logger.debug("Reset ignore patterns to defaults")
    
    def _get_device_config(self, device: Any, command: str) -> str:
        """Get configuration from device's cached command outputs"""
        try:
            # Check if device has command outputs stored
            command_outputs = None
            if hasattr(device, 'command_outputs') and device.command_outputs:
                command_outputs = device.command_outputs
            elif hasattr(device, 'get_command_outputs'):
                command_outputs = device.get_command_outputs()
            
            if not command_outputs:
                logger.debug(f"No command outputs found for device {getattr(device, 'device_id', 'Unknown')}")
                return ""
            
            # Try exact command match first
            if command in command_outputs:
                cmd_outputs = command_outputs[command]
                if cmd_outputs and isinstance(cmd_outputs, dict):
                    # Get the most recent output
                    timestamps = list(cmd_outputs.keys())
                    if timestamps:
                        latest_timestamp = max(timestamps)
                        output_data = cmd_outputs[latest_timestamp]
                        if isinstance(output_data, dict) and 'output' in output_data:
                            return output_data['output']
                        elif isinstance(output_data, str):
                            return output_data
            
            # Try fuzzy matching for similar commands
            command_lower = command.lower()
            for cmd_id, cmd_outputs in command_outputs.items():
                if cmd_id.lower() == command_lower or command_lower in cmd_id.lower():
                    if cmd_outputs and isinstance(cmd_outputs, dict):
                        timestamps = list(cmd_outputs.keys())
                        if timestamps:
                            latest_timestamp = max(timestamps)
                            output_data = cmd_outputs[latest_timestamp]
                            if isinstance(output_data, dict) and 'output' in output_data:
                                return output_data['output']
                            elif isinstance(output_data, str):
                                return output_data
            
            logger.debug(f"No output found for command '{command}' on device {getattr(device, 'device_id', 'Unknown')}")
            return ""
            
        except Exception as e:
            logger.error(f"Error getting device config: {e}")
            return ""
    
    def _get_command_output(self, device: Any, command: str) -> str:
        """Get command output from device's cached command outputs"""
        # Use the same logic as _get_device_config since they're essentially the same
        return self._get_device_config(device, command)
    
    def _preprocess_config(self, config: str, ignore_timestamps: bool = True, 
                          ignore_comments: bool = True) -> str:
        """
        Preprocess configuration to normalize for comparison
        
        Args:
            config: Configuration text
            ignore_timestamps: Whether to ignore timestamp lines
            ignore_comments: Whether to ignore comment lines
            
        Returns:
            Preprocessed configuration
        """
        try:
            lines = config.splitlines()
            processed_lines = []
            
            for line in lines:
                # Skip empty lines
                if not line.strip():
                    continue
                
                # Skip comment lines if requested
                if ignore_comments and line.strip().startswith('!'):
                    continue
                
                # Apply ignore patterns
                if any(re.match(pattern, line) for pattern in self.ignore_patterns):
                    continue
                
                # Remove trailing whitespace
                line = line.rstrip()
                
                processed_lines.append(line)
            
            return '\n'.join(processed_lines)
            
        except Exception as e:
            logger.error(f"Error preprocessing config: {e}")
            return config
    
    def _preprocess_show_output(self, output: str) -> str:
        """
        Preprocess show command output to normalize for comparison
        
        Args:
            output: Command output text
            
        Returns:
            Preprocessed output
        """
        try:
            lines = output.splitlines()
            processed_lines = []
            
            for line in lines:
                # Remove dynamic timestamps and counters
                line = re.sub(r'\d{2}:\d{2}:\d{2}', 'XX:XX:XX', line)  # Time stamps
                line = re.sub(r'\d+ packets', 'X packets', line)  # Packet counters
                line = re.sub(r'\d+ bytes', 'X bytes', line)  # Byte counters
                line = re.sub(r'uptime is \S+', 'uptime is X', line)  # Uptime
                
                processed_lines.append(line.rstrip())
            
            return '\n'.join(processed_lines)
            
        except Exception as e:
            logger.error(f"Error preprocessing show output: {e}")
            return output
    
    def find_config_sections_with_differences(self, comparison_result: ComparisonResult) -> Dict[str, List[Dict]]:
        """
        Group differences by configuration section
        
        Args:
            comparison_result: ComparisonResult object
            
        Returns:
            Dictionary grouping differences by section
        """
        sections = {}
        
        try:
            for diff in comparison_result.differences:
                section = diff.get('section', 'Unknown')
                
                if section not in sections:
                    sections[section] = []
                
                sections[section].append(diff)
            
        except Exception as e:
            logger.error(f"Error grouping differences by section: {e}")
        
        return sections
    
    def generate_summary_report(self, comparison_results: List[ComparisonResult]) -> str:
        """
        Generate a summary report for multiple comparisons
        
        Args:
            comparison_results: List of comparison results
            
        Returns:
            Summary report as text
        """
        try:
            report = []
            report.append("Configuration Comparison Summary")
            report.append("=" * 40)
            report.append("")
            
            total_comparisons = len(comparison_results)
            total_differences = sum(len(result.differences) for result in comparison_results)
            
            report.append(f"Total Comparisons: {total_comparisons}")
            report.append(f"Total Differences: {total_differences}")
            report.append("")
            
            for i, result in enumerate(comparison_results, 1):
                report.append(f"{i}. {result.device1_name} vs {result.device2_name}")
                report.append(f"   Differences: {len(result.differences)}")
                report.append(f"   Similarity: {result.statistics.get('similarity_ratio', 0):.2%}")
                report.append("")
            
            return '\n'.join(report)
            
        except Exception as e:
            logger.error(f"Error generating summary report: {e}")
            return "Error generating report" 