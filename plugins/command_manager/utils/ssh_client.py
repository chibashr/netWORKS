#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
SSH client utility for Command Manager plugin
"""

import time
import re
import socket
import paramiko
from loguru import logger


class SSHClient:
    """Client for connecting to network devices via SSH"""
    
    def __init__(self, host, username, password, enable_password="", port=22, timeout=10):
        """Initialize the SSH client"""
        self.host = host
        self.username = username
        self.password = password
        self.enable_password = enable_password
        self.port = port
        self.timeout = timeout
        
        self.client = None
        self.shell = None
        self.connected = False
        self.prompt = None
        
    def connect(self):
        """Connect to the device"""
        try:
            # Create SSH client
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect to the device
            self.client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=self.timeout,
                allow_agent=False,
                look_for_keys=False
            )
            
            # If we need to use enable mode, open shell for interactive commands
            if self.enable_password:
                # Open shell
                self.shell = self.client.invoke_shell()
                self.shell.settimeout(self.timeout)
                
                # Clear initial buffer
                time.sleep(1)
                output = self._read_output()
                
                # Try to detect prompt
                self.prompt = self._detect_prompt(output)
            
            self.connected = True
            return True
            
        except Exception as e:
            logger.error(f"SSH connection error: {e}")
            self.disconnect()
            raise Exception(f"Failed to connect to {self.host}: {str(e)}")
            
    def disconnect(self):
        """Disconnect from the device"""
        if self.shell:
            self.shell.close()
            self.shell = None
            
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
        self.shell.send("enable\n")
        time.sleep(0.5)
        
        # Check for password prompt
        output = self._read_output()
        if re.search(r"[Pp]assword", output):
            # Send enable password
            self.shell.send(f"{self.enable_password}\n")
            time.sleep(0.5)
            
            # Read output again
            output = self._read_output()
            
            # Try to detect new prompt
            new_prompt = self._detect_prompt(output)
            if new_prompt:
                self.prompt = new_prompt
                
    def execute(self, command):
        """Execute a command and return the output"""
        if not self.connected:
            raise Exception("Not connected")
        
        # If enable mode is required, use the shell to execute commands
        if self.enable_password and self.shell:
            return self._execute_shell(command)
        else:
            return self._execute_paramiko(command)
    
    def _execute_paramiko(self, command):
        """Execute command using paramiko's exec_command method"""
        try:
            # Execute command directly
            stdin, stdout, stderr = self.client.exec_command(command, timeout=self.timeout)
            
            # Get command output
            output = stdout.read().decode('utf-8', errors='ignore')
            error = stderr.read().decode('utf-8', errors='ignore')
            
            # Combine output and error
            full_output = f"{output}"
            if error:
                full_output += f"\nERROR: {error}"
                
            return full_output.strip()
        except Exception as e:
            logger.error(f"Error executing command via paramiko: {e}")
            return f"Error executing command: {str(e)}"
    
    def _execute_shell(self, command):
        """Execute command via interactive shell (for enable mode)"""
        # Clear buffer
        self._read_output()
        
        # Send command
        self.shell.send(f"{command}\n")
        
        # Wait for command to complete
        time.sleep(1)
        
        # Collect output until prompt is seen or timeout
        output = ""
        start_time = time.time()
        
        while time.time() - start_time < self.timeout:
            # Read available output
            new_output = self._read_output()
            output += new_output
            
            # Check if we've reached the prompt
            if self.prompt and re.search(re.escape(self.prompt), output):
                break
                
            # Short pause
            time.sleep(0.5)
            
        # Remove command echo and prompt from output
        output = self._clean_output(output, command)
        
        return output
        
    def _read_output(self):
        """Read available output from the shell"""
        if not self.shell:
            return ""
            
        output = ""
        try:
            # Check if data is available
            if self.shell.recv_ready():
                # Read available data
                output = self.shell.recv(65535).decode("utf-8", errors="ignore")
        except socket.timeout:
            pass
        except Exception as e:
            logger.error(f"Error reading SSH output: {e}")
            
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