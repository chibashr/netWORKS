#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Cisco Syntax Highlighter for ConfigMate Plugin

Provides syntax highlighting for Cisco IOS/NX-OS configuration files and templates.
"""

import re
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from PySide6.QtCore import Qt


class CiscoSyntaxHighlighter(QSyntaxHighlighter):
    """
    Syntax highlighter for Cisco IOS/NX-OS configurations and templates
    
    Highlights:
    - Commands and keywords
    - IP addresses and subnets
    - Interface names
    - Comments
    - Jinja2 template variables
    - Access lists and route maps
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Define text formats
        self.formats = {}
        self._setup_formats()
        
        # Define highlighting rules
        self.rules = []
        self._setup_rules()
    
    def _setup_formats(self):
        """Set up text formats for different syntax elements"""
        
        # Commands (blue)
        command_format = QTextCharFormat()
        command_format.setForeground(QColor(0, 0, 255))
        command_format.setFontWeight(QFont.Weight.Bold)
        self.formats['command'] = command_format
        
        # Keywords (dark blue)
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor(0, 0, 139))
        keyword_format.setFontWeight(QFont.Weight.Bold)
        self.formats['keyword'] = keyword_format
        
        # IP addresses (green)
        ip_format = QTextCharFormat()
        ip_format.setForeground(QColor(0, 128, 0))
        self.formats['ip'] = ip_format
        
        # Interface names (purple)
        interface_format = QTextCharFormat()
        interface_format.setForeground(QColor(128, 0, 128))
        self.formats['interface'] = interface_format
        
        # Comments (gray)
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor(128, 128, 128))
        comment_format.setFontItalic(True)
        self.formats['comment'] = comment_format
        
        # Jinja2 variables (red)
        jinja_format = QTextCharFormat()
        jinja_format.setForeground(QColor(255, 0, 0))
        jinja_format.setFontWeight(QFont.Weight.Bold)
        self.formats['jinja'] = jinja_format
        
        # Numbers (orange)
        number_format = QTextCharFormat()
        number_format.setForeground(QColor(255, 165, 0))
        self.formats['number'] = number_format
        
        # Strings (dark green)
        string_format = QTextCharFormat()
        string_format.setForeground(QColor(0, 100, 0))
        self.formats['string'] = string_format
    
    def _setup_rules(self):
        """Set up highlighting rules with regex patterns"""
        
        # Jinja2 template variables {{ variable }}
        self.rules.append((
            re.compile(r'\{\{.*?\}\}'),
            self.formats['jinja']
        ))
        
        # Jinja2 control structures {% ... %}
        self.rules.append((
            re.compile(r'\{%.*?%\}'),
            self.formats['jinja']
        ))
        
        # Comments (lines starting with !)
        self.rules.append((
            re.compile(r'^!.*$', re.MULTILINE),
            self.formats['comment']
        ))
        
        # IP addresses (IPv4)
        self.rules.append((
            re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?:/[0-9]{1,2})?\b'),
            self.formats['ip']
        ))
        
        # Interface names
        interface_pattern = r'\b(?:interface\s+)?(?:GigabitEthernet|FastEthernet|Ethernet|Serial|Loopback|Vlan|Port-channel|Tunnel)\d+(?:/\d+)*(?:\.\d+)?\b'
        self.rules.append((
            re.compile(interface_pattern, re.IGNORECASE),
            self.formats['interface']
        ))
        
        # Common Cisco commands
        commands = [
            'router', 'interface', 'ip', 'no', 'shutdown', 'description',
            'switchport', 'access', 'trunk', 'vlan', 'spanning-tree',
            'access-list', 'route-map', 'bgp', 'ospf', 'eigrp', 'rip',
            'hostname', 'enable', 'line', 'username', 'password', 'service',
            'logging', 'snmp-server', 'ntp', 'clock', 'banner', 'version',
            'boot', 'config-register', 'cdp', 'lldp'
        ]
        
        for command in commands:
            self.rules.append((
                re.compile(r'\b' + command + r'\b', re.IGNORECASE),
                self.formats['command']
            ))
        
        # Keywords
        keywords = [
            'permit', 'deny', 'any', 'host', 'eq', 'gt', 'lt', 'range',
            'established', 'log', 'in', 'out', 'both', 'auto', 'full',
            'half', 'duplex', 'speed', 'mtu', 'encapsulation', 'dot1q',
            'native', 'allowed', 'mode', 'dynamic', 'desirable', 'on',
            'off', 'priority', 'cost', 'hello-time', 'forward-time',
            'max-age', 'diameter', 'root'
        ]
        
        for keyword in keywords:
            self.rules.append((
                re.compile(r'\b' + keyword + r'\b', re.IGNORECASE),
                self.formats['keyword']
            ))
        
        # Numbers (standalone)
        self.rules.append((
            re.compile(r'\b\d+\b'),
            self.formats['number']
        ))
        
        # Quoted strings
        self.rules.append((
            re.compile(r'"[^"]*"'),
            self.formats['string']
        ))
    
    def highlightBlock(self, text):
        """Apply syntax highlighting to a block of text"""
        
        # Apply all rules
        for pattern, format_obj in self.rules:
            for match in pattern.finditer(text):
                start = match.start()
                length = match.end() - start
                self.setFormat(start, length, format_obj) 