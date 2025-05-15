#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Telnet client utility for Command Manager plugin
"""

import time
import re
import socket
import telnetlib
from loguru import logger


class TelnetClient:
    """Client for connecting to network devices via Telnet"""
    
    def __init__(self, host, username, password, enable_password="", port=23, timeout=10):
        """Initialize the Telnet client"""
        self.host = host
        self.username = username
        self.password = password
        self.enable_password = enable_password
        self.port = port
        self.timeout = timeout
        
        self.client = None
        self.connected = False
        self.prompt = None
        
    def connect(self):
        """Connect to the device"""
        try:
            # Create Telnet client
            self.client = telnetlib.Telnet(self.host, self.port, self.timeout)
            
            # Wait for login prompt
            index, match, output = self.client.expect([
                b"[Uu]sername[: ]*", 
                b"[Ll]ogin[: ]*"
            ], timeout=self.timeout)
            
            if index < 0:
                raise Exception("Login prompt not found")
                
            # Send username
            self.client.write(f"{self.username}\n".encode())
            
            # Wait for password prompt
            index, match, output = self.client.expect([
                b"[Pp]assword[: ]*"
            ], timeout=self.timeout)
            
            if index < 0:
                raise Exception("Password prompt not found")
                
            # Send password
            self.client.write(f"{self.password}\n".encode())
            
            # Wait for command prompt
            time.sleep(2)
            output = self.client.read_very_eager().decode("utf-8", errors="ignore")
            
            # Try to detect prompt
            self.prompt = self._detect_prompt(output)
            
            if not self.prompt:
                raise Exception("Command prompt not found")
                
            self.connected = True
            return True
            
        except Exception as e:
            logger.error(f"Telnet connection error: {e}")
            self.disconnect()
            raise Exception(f"Failed to connect to {self.host}: {str(e)}")
            
    def disconnect(self):
        """Disconnect from the device"""
        if self.client:
            self.client.close()
            self.client = None
            
        self.connected = False
        
    def enable(self):
        """Enter enable mode"""
        if not self.connected:
            raise Exception("Not connected")
            
        if not self.enable_password:
            return
            
        # Send enable command
        self.client.write(b"enable\n")
        time.sleep(0.5)
        
        # Check for password prompt
        output = self.client.read_very_eager().decode("utf-8", errors="ignore")
        if re.search(r"[Pp]assword", output):
            # Send enable password
            self.client.write(f"{self.enable_password}\n".encode())
            time.sleep(1)
            
            # Read output again
            output = self.client.read_very_eager().decode("utf-8", errors="ignore")
            
            # Try to detect new prompt
            new_prompt = self._detect_prompt(output)
            if new_prompt:
                self.prompt = new_prompt
                
    def execute(self, command):
        """Execute a command and return the output"""
        if not self.connected:
            raise Exception("Not connected")
            
        # Clear buffer
        self.client.read_very_eager()
        
        # Send command
        self.client.write(f"{command}\n".encode())
        
        # Wait for command to complete
        time.sleep(1)
        
        # Collect output until prompt is seen or timeout
        output = ""
        start_time = time.time()
        
        while time.time() - start_time < self.timeout:
            # Read available output
            try:
                new_output = self.client.read_very_eager().decode("utf-8", errors="ignore")
                output += new_output
                
                # Check if we've reached the prompt
                if self.prompt and re.search(re.escape(self.prompt), output):
                    break
                    
                # If no new output and we don't see the prompt, try reading more
                if not new_output:
                    time.sleep(0.5)
            except EOFError:
                # Connection closed
                self.connected = False
                break
            except Exception as e:
                logger.error(f"Error reading Telnet output: {e}")
                break
                
        # Remove command echo and prompt from output
        output = self._clean_output(output, command)
        
        return output
        
    def _detect_prompt(self, output):
        """Try to detect the command prompt"""
        if not output:
            return None
            
        # Look for common prompt patterns
        prompt_patterns = [
            r"[\r\n]([A-Za-z0-9_\-\.\(\)\/]+[#>])\s*$",  # Common Cisco-like prompts
            r"[\r\n]([A-Za-z0-9_\-\.]+[@][A-Za-z0-9_\-\.]+[#$%])\s*$"  # Linux-like prompts
        ]
        
        for pattern in prompt_patterns:
            match = re.search(pattern, output)
            if match:
                return match.group(1)
                
        # If no pattern matches, use last non-empty line
        lines = output.splitlines()
        for line in reversed(lines):
            line = line.strip()
            if line:
                # Use up to 20 chars of the last line as prompt
                return line[-20:] if len(line) > 20 else line
                
        return None
        
    def _clean_output(self, output, command):
        """Clean up command output by removing echoed command and prompt"""
        # Remove the echoed command
        output = re.sub(re.escape(command) + r"[\r\n]+", "", output, count=1)
        
        # Remove the prompt at the end
        if self.prompt:
            output = re.sub(re.escape(self.prompt) + r"\s*$", "", output)
            
        # Strip extra whitespace
        output = output.strip()
        
        return output 