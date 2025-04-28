#!/usr/bin/env python3
# NetSCAN - Plugin Manager

import os
import json
import importlib.util
import logging
import sys
from pathlib import Path
from typing import Dict, List, Callable

class PluginManager:
    """Manager for NetSCAN plugins."""
    
    def __init__(self, config_path, skip_discovery=False):
        self.config_path = config_path
        self.plugins = {}
        self.logger = logging.getLogger(__name__)
        self.config = self.load_config()
        self.plugin_dir = "plugins"
        self.hooks = {}  # Dictionary of registered hooks
        self.plugin_apis = {}  # Dictionary of plugin APIs
        self.menu_callbacks = []
        self.skip_discovery = skip_discovery
        self.main_window = None  # Reference to main window for event processing
        self.plugin_errors = {}  # Dictionary to track plugin loading errors
        self.plugin_requirements = {}  # Dictionary to track plugin requirements
        
        # Create plugin directory if it doesn't exist
        if not os.path.exists(self.plugin_dir):
            os.makedirs(self.plugin_dir)
            self.logger.info(f"Created plugin directory: {self.plugin_dir}")
        
        # Add plugins directory to sys.path if it's not already there
        absolute_plugin_dir = os.path.abspath(self.plugin_dir)
        if absolute_plugin_dir not in sys.path:
            sys.path.insert(0, absolute_plugin_dir)
            self.logger.info(f"Added plugins directory to Python path: {absolute_plugin_dir}")
            
        # Check for parent directory of plugins to support absolute imports
        parent_dir = os.path.dirname(absolute_plugin_dir)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
            self.logger.info(f"Added parent directory to Python path: {parent_dir}")
            
        # Discover and load plugins
        if not skip_discovery:
            self.discover_plugins()
        else:
            self.logger.warning("Plugin discovery skipped - operating in minimal mode")
    
    def load_config(self):
        """Load plugin configuration."""
        config = {"plugins": {}}
        
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading plugin config: {str(e)}")
        else:
            # Create default configuration
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
        
        return config
    
    def save_config(self):
        """Save plugin configuration."""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            self.logger.info("Plugin configuration saved")
            return True
        except Exception as e:
            self.logger.error(f"Error saving plugin config: {str(e)}")
            return False
    
    def discover_plugins(self):
        """Discover available plugins."""
        if not os.path.exists(self.plugin_dir):
            self.logger.warning(f"Plugin directory does not exist: {os.path.abspath(self.plugin_dir)}")
            return
        
        self.logger.info(f"Discovering plugins in {self.plugin_dir}")
        self.logger.debug(f"Absolute path: {os.path.abspath(self.plugin_dir)}")
        
        # Keep track of discovery statistics
        num_dirs_scanned = 0
        num_plugins_found = 0
        num_plugins_valid = 0
        
        def scan_directory(directory):
            """Recursively scan directory for plugins."""
            nonlocal num_dirs_scanned, num_plugins_found, num_plugins_valid
            
            try:
                items = os.listdir(directory)
                self.logger.debug(f"Scanning directory: {directory} ({len(items)} items)")
                num_dirs_scanned += 1
                
                for item in items:
                    plugin_path = os.path.join(directory, item)
                    
                    # Skip non-directories
                    if not os.path.isdir(plugin_path):
                        self.logger.debug(f"Skipping non-directory: {plugin_path}")
                        continue
                    
                    self.logger.debug(f"Checking directory: {plugin_path}")
                    
                    # Check for manifest.json
                    manifest_path = os.path.join(plugin_path, "manifest.json")
                    if os.path.exists(manifest_path):
                        num_plugins_found += 1
                        try:
                            self.logger.debug(f"Found manifest: {manifest_path}")
                            with open(manifest_path, 'r') as f:
                                manifest_content = f.read()
                                self.logger.debug(f"Manifest content: {manifest_content[:100]}...")
                                manifest = json.loads(manifest_content)
                            
                            plugin_id = manifest.get("name")
                            if not plugin_id:
                                self.logger.warning(f"Plugin manifest missing 'name' field: {plugin_path}")
                                continue
                            
                            # Check for required main file
                            main_file = manifest.get("main", "main.py")
                            main_path = os.path.join(plugin_path, main_file)
                            if not os.path.exists(main_path):
                                self.logger.warning(f"Plugin main file not found: {main_path}")
                                continue
                                
                            # Check if init_plugin function exists
                            try:
                                with open(main_path, 'r') as f:
                                    content = f.read()
                                    if "init_plugin" not in content:
                                        self.logger.warning(f"Plugin main file doesn't contain init_plugin function: {main_path}")
                            except Exception as e:
                                self.logger.warning(f"Error reading plugin main file: {main_path} - {str(e)}")
                            
                            self.logger.info(f"Found plugin: {plugin_id} in {plugin_path}")
                            num_plugins_valid += 1
                            
                            # Store plugin info
                            self.register_plugin(plugin_id, plugin_path, manifest)
                            
                        except json.JSONDecodeError as e:
                            self.logger.error(f"Invalid JSON in plugin manifest {manifest_path}: {str(e)}")
                            self.logger.debug(f"JSON error at position {e.pos}: {e.msg}")
                            with open(manifest_path, 'r') as f:
                                lines = f.readlines()
                                line_num = 1
                                pos = 0
                                for i, line in enumerate(lines):
                                    if pos + len(line) >= e.pos:
                                        line_num = i + 1
                                        char_pos = e.pos - pos
                                        self.logger.debug(f"Error at line {line_num}, character {char_pos}")
                                        self.logger.debug(f"Line content: {line.strip()}")
                                        break
                                    pos += len(line)
                        except Exception as e:
                            self.logger.error(f"Error loading plugin manifest {plugin_path}: {str(e)}", exc_info=True)
                    else:
                        # No manifest.json found, recursively check subdirectories
                        scan_directory(plugin_path)
            except PermissionError as e:
                self.logger.error(f"Permission denied when scanning directory: {directory} - {str(e)}")
            except Exception as e:
                self.logger.error(f"Error scanning directory {directory}: {str(e)}", exc_info=True)
        
        # Start recursive scan from plugin directory
        try:
            scan_directory(self.plugin_dir)
            
            # Log summary of plugin discovery
            self.logger.info(f"Plugin discovery summary: {num_dirs_scanned} directories scanned, "
                             f"{num_plugins_found} potential plugins found, "
                             f"{num_plugins_valid} valid plugins registered")
            
            if num_plugins_valid == 0:
                self.logger.warning("No valid plugins were found. This may indicate a problem with the plugin directory structure.")
                # List contents of plugin directory to help diagnose issues
                self.logger.debug(f"Contents of plugin directory '{self.plugin_dir}':")
                try:
                    self._list_directory_contents(self.plugin_dir)
                except Exception as e:
                    self.logger.error(f"Error listing plugin directory contents: {str(e)}")
                    
        except Exception as e:
            self.logger.error(f"Error during plugin discovery: {str(e)}", exc_info=True)
    
    def _list_directory_contents(self, directory, depth=0, max_depth=2):
        """List directory contents recursively for debugging purposes."""
        try:
            if depth > max_depth:
                return
                
            items = os.listdir(directory)
            for item in items:
                path = os.path.join(directory, item)
                if os.path.isdir(path):
                    self.logger.debug(f"{'  ' * depth}[DIR] {item}/")
                    self._list_directory_contents(path, depth + 1, max_depth)
                else:
                    size = os.path.getsize(path)
                    self.logger.debug(f"{'  ' * depth}[FILE] {item} ({size} bytes)")
        except Exception as e:
            self.logger.error(f"Error listing directory contents for {directory}: {str(e)}")
    
    def is_core_plugin(self, plugin_id, plugin_path=None):
        """Check if a plugin is a core plugin based on ID prefix or location."""
        # Check if plugin ID starts with 'core-'
        is_core_by_id = plugin_id.startswith("core-")
        
        # Check if plugin is in the core directory
        is_core_by_location = False
        if plugin_path:
            plugin_path = os.path.normpath(plugin_path)
            is_core_by_location = os.path.sep + "core" + os.path.sep in plugin_path
        
        return is_core_by_id or is_core_by_location
    
    def register_plugin(self, plugin_id, plugin_path, manifest):
        """Register a discovered plugin."""
        self.logger.info(f"Registering plugin: {plugin_id}")
        
        # Check for README.md and API documentation
        readme_path = os.path.join(plugin_path, "README.md")
        if not os.path.exists(readme_path):
            self.logger.warning(f"Plugin {plugin_id} is missing README.md file")
            
        # Check for API documentation (either in manifest or API.md)
        has_api_docs = False
        if "exports" in manifest or "api" in manifest:
            has_api_docs = True
            self.logger.info(f"Plugin {plugin_id} has API documentation in manifest")
        else:
            api_doc_path = os.path.join(plugin_path, "API.md")
            if os.path.exists(api_doc_path):
                has_api_docs = True
                self.logger.info(f"Plugin {plugin_id} has API.md documentation")
        
        if not has_api_docs and not self.is_core_plugin(plugin_id, plugin_path):
            self.logger.warning(f"Plugin {plugin_id} has no API documentation (neither in manifest nor API.md)")
        
        # Check if plugin is already in config, otherwise add with default (disabled)
        if plugin_id not in self.config["plugins"]:
            # Enable core plugins by default and lock them
            is_core = self.is_core_plugin(plugin_id, plugin_path)
            self.config["plugins"][plugin_id] = {
                "enabled": is_core,
                "locked": is_core,
                "settings": {}
            }
            self.save_config()
            self.logger.info(f"Added plugin {plugin_id} to config (enabled: {is_core}, locked: {is_core})")
        
        # Store plugin info including documentation status
        self.plugins[plugin_id] = {
            "id": plugin_id,
            "path": plugin_path,
            "manifest": manifest,
            "instance": None,
            "enabled": self.config["plugins"][plugin_id]["enabled"],
            "locked": self.config["plugins"][plugin_id].get("locked", False),
            "has_readme": os.path.exists(readme_path),
            "has_api_docs": has_api_docs
        }
        
        self.logger.info(f"Registered plugin: {plugin_id} - {manifest.get('displayName', plugin_id)}")
        
        # Load the plugin if enabled
        if self.plugins[plugin_id]["enabled"]:
            self.logger.info(f"Auto-loading enabled plugin: {plugin_id}")
            self.load_plugin(plugin_id)
    
    def install_plugin_requirements(self, plugin_path):
        """Install requirements for a plugin if they exist.
        
        Args:
            plugin_path: Path to the plugin directory
            
        Returns:
            bool: True if successful, False otherwise
        """
        requirements_file = os.path.join(plugin_path, "requirements.txt")
        if not os.path.exists(requirements_file):
            self.logger.debug(f"No requirements.txt found in {plugin_path}")
            return True
            
        try:
            self.logger.info(f"Installing requirements for plugin in {plugin_path}")
            import subprocess
            import sys
            import threading
            import time
            
            # Flag to track installation completion
            install_completed = threading.Event()
            install_success = [True]  # Use list so it can be modified in thread
            install_error = [None]    # Store error message
            
            # Thread function to perform installation
            def install_thread():
                try:
                    # Use the current Python executable (main application's venv)
                    python_executable = sys.executable
                    
                    # First, upgrade pip if needed
                    self.logger.debug("Checking pip installation...")
                    upgrade_result = subprocess.run(
                        [python_executable, "-m", "pip", "install", "--upgrade", "pip"],
                        capture_output=True,
                        text=True,
                        timeout=30  # 30 second timeout
                    )
                    
                    if upgrade_result.returncode != 0:
                        self.logger.warning(f"Failed to upgrade pip: {upgrade_result.stderr}")
                    
                    # Install requirements using pip with verbose output
                    self.logger.debug("Installing plugin requirements to main venv...")
                    result = subprocess.run(
                        [python_executable, "-m", "pip", "install", "-r", requirements_file, "--no-cache-dir"],
                        capture_output=True,
                        text=True,
                        timeout=60  # 60 second timeout
                    )
                    
                    if result.returncode != 0:
                        # If installation failed, try installing packages one by one
                        self.logger.warning("Failed to install all requirements at once, trying individual packages...")
                        
                        with open(requirements_file, 'r') as f:
                            requirements = f.readlines()
                        
                        # Store installed requirements for potential uninstallation later
                        installed_requirements = []
                        
                        for req in requirements:
                            req = req.strip()
                            if req and not req.startswith('#'):
                                self.logger.debug(f"Installing requirement: {req}")
                                result = subprocess.run(
                                    [python_executable, "-m", "pip", "install", req, "--no-cache-dir"],
                                    capture_output=True,
                                    text=True,
                                    timeout=30  # 30 second timeout per package
                                )
                                if result.returncode != 0:
                                    self.logger.error(f"Failed to install {req}: {result.stderr}")
                                    install_success[0] = False
                                    install_error[0] = f"Failed to install {req}: {result.stderr}"
                                    break
                                else:
                                    installed_requirements.append(req)
                        
                        if install_success[0]:
                            self.logger.info("Successfully installed all requirements individually")
                            
                        # Store the requirements associated with this plugin
                        plugin_id = os.path.basename(plugin_path)
                        if not hasattr(self, 'plugin_requirements'):
                            self.plugin_requirements = {}
                        self.plugin_requirements[plugin_id] = installed_requirements
                    else:
                        # Successfully installed all requirements at once
                        self.logger.info("Successfully installed all requirements")
                        
                        # Store the requirements associated with this plugin
                        plugin_id = os.path.basename(plugin_path)
                        if not hasattr(self, 'plugin_requirements'):
                            self.plugin_requirements = {}
                            
                        # Parse requirements from file
                        with open(requirements_file, 'r') as f:
                            requirements = [line.strip() for line in f.readlines() 
                                           if line.strip() and not line.startswith('#')]
                        self.plugin_requirements[plugin_id] = requirements
                
                except Exception as e:
                    self.logger.error(f"Error in installation thread: {str(e)}", exc_info=True)
                    install_success[0] = False
                    install_error[0] = str(e)
                finally:
                    # Signal that installation is complete
                    install_completed.set()
            
            # Start installation in a separate thread
            install_thread = threading.Thread(target=install_thread)
            install_thread.daemon = True  # Make thread daemon so it doesn't block program exit
            install_thread.start()
            
            # Wait for installation to complete with timeout
            installation_timeout = 180  # 3 minutes
            installation_start = time.time()
            
            while not install_completed.is_set():
                # Check if timeout exceeded
                if time.time() - installation_start > installation_timeout:
                    self.logger.error(f"Plugin requirement installation timed out after {installation_timeout} seconds")
                    return False
                
                # Wait a bit before checking again
                time.sleep(0.5)
                
                # Allow events to be processed while waiting
                if hasattr(self, 'main_window') and self.main_window:
                    # If we have a reference to a main window, process events
                    from PySide6.QtCore import QCoreApplication
                    QCoreApplication.processEvents()
            
            # Check installation result
            if not install_success[0]:
                self.logger.error(f"Plugin requirement installation failed: {install_error[0]}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error installing plugin requirements: {str(e)}", exc_info=True)
            return False

    def load_plugin(self, plugin_id):
        """Load and initialize a plugin."""
        if plugin_id not in self.plugins:
            error_msg = f"Plugin {plugin_id} not found"
            self.logger.error(error_msg)
            self.plugin_errors[plugin_id] = error_msg
            return False
            
        plugin_info = self.plugins[plugin_id]
        if plugin_info["instance"]:
            self.logger.warning(f"Plugin {plugin_id} already loaded")
            # Clear any previous errors if the plugin is already loaded
            if plugin_id in self.plugin_errors:
                del self.plugin_errors[plugin_id]
            return True
        
        # Timeouts for plugin loading stages
        requirement_timeout = 30  # seconds
        plugin_init_timeout = 10  # seconds
            
        try:
            # Create plugin API first - must exist before plugin init
            plugin_api = self._create_plugin_api(plugin_id)
            self.plugin_apis[plugin_id] = plugin_api
            
            # Check plugin manifest for main module
            manifest = plugin_info["manifest"]
            main_module = manifest.get("main", "main.py")
            
            # Get full path to main module
            main_path = os.path.join(plugin_info["path"], main_module)
            if not os.path.exists(main_path):
                error_msg = f"Plugin main module not found: {main_path}"
                self.logger.error(error_msg)
                self.plugin_errors[plugin_id] = error_msg
                return False
                
            # Install plugin requirements with timeout
            import threading
            import time
            
            requirement_start_time = time.time()
            requirement_thread_result = [False]
            requirement_thread_complete = threading.Event()
            
            def requirement_thread():
                """Thread for installing requirements with timeout"""
                try:
                    result = self.install_plugin_requirements(plugin_info["path"])
                    requirement_thread_result[0] = result
                except Exception as e:
                    error_msg = f"Error installing requirements for plugin {plugin_id}: {str(e)}"
                    self.logger.error(error_msg, exc_info=True)
                    self.plugin_errors[plugin_id] = error_msg
                    requirement_thread_result[0] = False
                finally:
                    requirement_thread_complete.set()
            
            # Start thread for requirement installation
            thread = threading.Thread(target=requirement_thread)
            thread.daemon = True
            thread.start()
            
            # Wait for requirements installation with timeout
            while not requirement_thread_complete.is_set():
                if time.time() - requirement_start_time > requirement_timeout:
                    error_msg = f"Plugin {plugin_id} requirement installation timed out"
                    self.logger.error(error_msg)
                    self.plugin_errors[plugin_id] = error_msg
                    return False
                time.sleep(0.1)
                
                # Process events to keep UI responsive
                from PySide6.QtCore import QCoreApplication
                QCoreApplication.processEvents()
            
            if not requirement_thread_result[0]:
                error_msg = f"Failed to install requirements for plugin {plugin_id}"
                self.logger.error(error_msg)
                if plugin_id not in self.plugin_errors:  # Only set if not already set in thread
                    self.plugin_errors[plugin_id] = error_msg
                return False
                
            # Import plugin module
            try:
                # Use importlib to load the module
                spec = importlib.util.spec_from_file_location(
                    f"plugin_{plugin_id.replace('-', '_')}", 
                    main_path
                )
                module = importlib.util.module_from_spec(spec)
                
                # Add plugin's directory to sys.path temporarily
                original_path = sys.path.copy()
                if plugin_info["path"] not in sys.path:
                    sys.path.insert(0, plugin_info["path"])
                
                # Execute the module with timeout
                init_start_time = time.time()
                init_thread_result = [None]
                init_thread_complete = threading.Event()
                
                def init_thread():
                    """Thread for module initialization with timeout"""
                    try:
                        spec.loader.exec_module(module)
                        init_thread_result[0] = module
                    except Exception as e:
                        error_msg = f"Error executing module for plugin {plugin_id}: {str(e)}"
                        self.logger.error(error_msg, exc_info=True)
                        self.plugin_errors[plugin_id] = error_msg
                        init_thread_result[0] = None
                    finally:
                        init_thread_complete.set()
                
                # Start thread for module initialization
                thread = threading.Thread(target=init_thread)
                thread.daemon = True
                thread.start()
                
                # Wait for module initialization with timeout
                while not init_thread_complete.is_set():
                    if time.time() - init_start_time > plugin_init_timeout:
                        error_msg = f"Plugin {plugin_id} module initialization timed out"
                        self.logger.error(error_msg)
                        self.plugin_errors[plugin_id] = error_msg
                        # Restore original sys.path
                        sys.path = original_path
                        return False
                    time.sleep(0.1)
                    
                    # Process events to keep UI responsive
                    QCoreApplication.processEvents()
                
                # If module initialization failed
                if init_thread_result[0] is None:
                    # Restore original sys.path
                    sys.path = original_path
                    error_msg = f"Failed to initialize module for plugin {plugin_id}"
                    self.logger.error(error_msg)
                    if plugin_id not in self.plugin_errors:  # Only set if not already set in thread
                        self.plugin_errors[plugin_id] = error_msg
                    return False
                
                # Module initialized successfully
                module = init_thread_result[0]
                
                # Restore original sys.path
                sys.path = original_path
                
                # Check if module has init_plugin function
                if not hasattr(module, "init_plugin"):
                    error_msg = f"Plugin {plugin_id} is missing init_plugin function"
                    self.logger.error(error_msg)
                    self.plugin_errors[plugin_id] = error_msg
                    return False
                
                # Initialize plugin with its API with timeout
                plugin_start_time = time.time()
                plugin_thread_result = [None]
                plugin_thread_complete = threading.Event()
                
                def plugin_thread():
                    """Thread for plugin initialization with timeout"""
                    try:
                        plugin_instance = module.init_plugin(plugin_api)
                        plugin_thread_result[0] = plugin_instance
                    except Exception as e:
                        error_msg = f"Error initializing plugin {plugin_id}: {str(e)}"
                        self.logger.error(error_msg, exc_info=True)
                        self.plugin_errors[plugin_id] = error_msg
                        plugin_thread_result[0] = None
                    finally:
                        plugin_thread_complete.set()
                
                # Start thread for plugin initialization
                thread = threading.Thread(target=plugin_thread)
                thread.daemon = True
                thread.start()
                
                # Wait for plugin initialization with timeout
                while not plugin_thread_complete.is_set():
                    if time.time() - plugin_start_time > plugin_init_timeout:
                        error_msg = f"Plugin {plugin_id} initialization timed out"
                        self.logger.error(error_msg)
                        self.plugin_errors[plugin_id] = error_msg
                        return False
                    time.sleep(0.1)
                    
                    # Process events to keep UI responsive
                    QCoreApplication.processEvents()
                
                # If plugin initialization failed
                if plugin_thread_result[0] is None:
                    error_msg = f"Failed to initialize plugin {plugin_id}"
                    self.logger.error(error_msg)
                    if plugin_id not in self.plugin_errors:  # Only set if not already set in thread
                        self.plugin_errors[plugin_id] = error_msg
                    return False
                
                # Plugin initialized successfully
                plugin_instance = plugin_thread_result[0]
                plugin_info["instance"] = plugin_instance
                plugin_info["module"] = module
                
                # Ensure plugin has a cleanup method
                if not hasattr(plugin_instance, "cleanup"):
                    self.logger.warning(f"Plugin {plugin_id} has no cleanup method")
                
                self.logger.info(f"Successfully loaded plugin {plugin_id}")
                
                # Clear any errors since the plugin loaded successfully
                if plugin_id in self.plugin_errors:
                    del self.plugin_errors[plugin_id]
                
                return True
                
            except ImportError as e:
                error_msg = f"Error importing plugin {plugin_id}: {str(e)}"
                self.logger.error(error_msg, exc_info=True)
                self.plugin_errors[plugin_id] = error_msg
                return False
                
        except Exception as e:
            error_msg = f"Error loading plugin {plugin_id}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.plugin_errors[plugin_id] = error_msg
            return False
    
    def uninstall_plugin_requirements(self, plugin_id):
        """Uninstall requirements associated with a plugin.
        
        Args:
            plugin_id: The ID of the plugin
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not hasattr(self, 'plugin_requirements') or plugin_id not in self.plugin_requirements:
            # No requirements to uninstall
            return True
            
        try:
            self.logger.info(f"Uninstalling requirements for plugin {plugin_id}")
            import subprocess
            import sys
            
            python_executable = sys.executable
            requirements = self.plugin_requirements[plugin_id]
            
            # Check which packages are safe to uninstall (not used by other plugins)
            packages_to_uninstall = []
            
            for req in requirements:
                # Parse package name from requirement (remove version specifiers)
                package_name = req.split('==')[0].split('>=')[0].split('<=')[0].split('>')[0].split('<')[0].strip()
                
                # Check if other enabled plugins need this package
                package_required_elsewhere = False
                for other_id, other_reqs in self.plugin_requirements.items():
                    if other_id != plugin_id and other_id in self.plugins and self.plugins[other_id]["enabled"]:
                        # Check if any requirement in the other plugin matches this package
                        for other_req in other_reqs:
                            other_pkg = other_req.split('==')[0].split('>=')[0].split('<=')[0].split('>')[0].split('<')[0].strip()
                            if other_pkg == package_name:
                                package_required_elsewhere = True
                                break
                    
                    if package_required_elsewhere:
                        break
                
                if not package_required_elsewhere:
                    packages_to_uninstall.append(package_name)
            
            # Uninstall packages that are not needed by other plugins
            for package_name in packages_to_uninstall:
                self.logger.debug(f"Uninstalling package: {package_name}")
                result = subprocess.run(
                    [python_executable, "-m", "pip", "uninstall", "-y", package_name],
                    capture_output=True,
                    text=True,
                    timeout=30  # 30 second timeout per package
                )
                
                if result.returncode != 0:
                    self.logger.warning(f"Failed to uninstall {package_name}: {result.stderr}")
            
            # Remove the requirements from tracking
            del self.plugin_requirements[plugin_id]
            return True
            
        except Exception as e:
            self.logger.error(f"Error uninstalling plugin requirements: {str(e)}", exc_info=True)
            return False

    def unload_plugin(self, plugin_id):
        """Unload a plugin."""
        if plugin_id not in self.plugins:
            return False
        
        plugin_info = self.plugins[plugin_id]
        
        # Skip if not loaded
        if plugin_info["instance"] is None:
            return True
        
        try:
            # Call plugin cleanup if available
            instance = plugin_info["instance"]
            if hasattr(instance, "cleanup"):
                instance.cleanup()
            
            # Remove plugin's hooks
            for hook_name in list(self.hooks.keys()):
                self.hooks[hook_name] = [
                    (cb_plugin_id, callback) for cb_plugin_id, callback in self.hooks[hook_name]
                    if cb_plugin_id != plugin_id
                ]
                if not self.hooks[hook_name]:
                    del self.hooks[hook_name]
            
            # Clear plugin instance
            plugin_info["instance"] = None
            plugin_info["module"] = None
            
            self.logger.info(f"Unloaded plugin: {plugin_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error unloading plugin {plugin_id}: {str(e)}")
            return False
    
    def enable_plugin(self, plugin_id):
        """Enable a plugin."""
        if plugin_id not in self.plugins:
            return False
        
        # Cannot enable/disable core plugins
        plugin_info = self.plugins[plugin_id]
        if self.is_core_plugin(plugin_id, plugin_info["path"]):
            self.logger.warning(f"Cannot enable/disable core plugin: {plugin_id}")
            return False
        
        self.plugins[plugin_id]["enabled"] = True
        self.config["plugins"][plugin_id]["enabled"] = True
        self.save_config()
        
        # Load the plugin
        success = self.load_plugin(plugin_id)
        
        # Show restart dialog if there's a main window
        if self.main_window:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(
                self.main_window,
                "Plugin Enabled",
                f"Plugin '{plugin_info['manifest'].get('displayName', plugin_id)}' has been enabled.\n\n"
                "For full functionality, it is recommended to restart the application."
            )
        
        return success
    
    def disable_plugin(self, plugin_id):
        """Disable a plugin."""
        if plugin_id not in self.plugins:
            return False
        
        # Cannot enable/disable core plugins
        plugin_info = self.plugins[plugin_id]
        if self.is_core_plugin(plugin_id, plugin_info["path"]):
            self.logger.warning(f"Cannot enable/disable core plugin: {plugin_id}")
            return False
        
        # Unload the plugin
        success = self.unload_plugin(plugin_id)
        
        # Uninstall the plugin requirements
        if success:
            self.uninstall_plugin_requirements(plugin_id)
        
        self.plugins[plugin_id]["enabled"] = False
        self.config["plugins"][plugin_id]["enabled"] = False
        self.save_config()
        
        # Show restart dialog if there's a main window
        if self.main_window:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(
                self.main_window,
                "Plugin Disabled",
                f"Plugin '{plugin_info['manifest'].get('displayName', plugin_id)}' has been disabled.\n\n"
                "For full functionality, it is recommended to restart the application."
            )
        
        return success
    
    def register_hook(self, hook_name, plugin_id, callback):
        """Register a hook callback for a plugin."""
        if hook_name not in self.hooks:
            self.hooks[hook_name] = []
        
        self.hooks[hook_name].append((plugin_id, callback))
        self.logger.debug(f"Plugin {plugin_id} registered hook: {hook_name}")
        return True
    
    def trigger_hook(self, hook_name, *args, **kwargs):
        """Trigger a hook, calling all registered callbacks."""
        if hook_name not in self.hooks:
            return []
        
        results = []
        for plugin_id, callback in self.hooks[hook_name]:
            try:
                result = callback(*args, **kwargs)
                results.append((plugin_id, result))
            except Exception as e:
                self.logger.error(f"Error in plugin {plugin_id} hook {hook_name}: {str(e)}")
        
        return results
    
    def send_message(self, target_plugin_id, message):
        """Send a message to a specific plugin."""
        if target_plugin_id not in self.plugins or not self.plugins[target_plugin_id]["enabled"]:
            return False
        
        instance = self.plugins[target_plugin_id]["instance"]
        if instance and hasattr(instance, "handle_message"):
            try:
                instance.handle_message(message)
                return True
            except Exception as e:
                self.logger.error(f"Error sending message to plugin {target_plugin_id}: {str(e)}")
        
        return False
    
    def broadcast(self, message):
        """Broadcast a message to all plugins."""
        results = {}
        for plugin_id, plugin_info in self.plugins.items():
            if plugin_info["enabled"] and plugin_info["instance"]:
                instance = plugin_info["instance"]
                if hasattr(instance, "handle_message"):
                    try:
                        result = instance.handle_message(message)
                        results[plugin_id] = result
                    except Exception as e:
                        self.logger.error(f"Error broadcasting to plugin {plugin_id}: {str(e)}")
        
        return results
    
    def get_plugin_ui_components(self, panel_name):
        """Get UI components from plugins for the specified panel."""
        components = []
        for plugin_id, plugin_info in self.plugins.items():
            if not plugin_info["enabled"] or not plugin_info["instance"]:
                continue
            
            # Check if plugin has UI components for this panel
            ui_config = plugin_info["manifest"].get("ui", {})
            panels = ui_config.get("panels", [])
            
            if panel_name in panels and hasattr(plugin_info["instance"], "get_ui_component"):
                try:
                    component = plugin_info["instance"].get_ui_component(panel_name)
                    if component:
                        components.append((plugin_id, component))
                except Exception as e:
                    self.logger.error(f"Error getting UI component from plugin {plugin_id}: {str(e)}")
        
        return components

    def load_plugins(self):
        """Load all enabled plugins."""
        successfully_loaded = []
        failed_plugins = []
        
        self.logger.info("Loading enabled plugins...")
        
        for plugin_id, plugin_info in self.plugins.items():
            if plugin_info["enabled"]:
                self.logger.info(f"Loading plugin: {plugin_id}")
                try:
                    if self.load_plugin(plugin_id):
                        successfully_loaded.append(plugin_id)
                    else:
                        failed_plugins.append(plugin_id)
                        self.logger.error(f"Failed to load plugin: {plugin_id}")
                except Exception as e:
                    failed_plugins.append(plugin_id)
                    self.logger.error(f"Error loading plugin {plugin_id}: {str(e)}", exc_info=True)
                
                # Process events to keep UI responsive
                if self.main_window:
                    from PySide6.QtCore import QCoreApplication
                    QCoreApplication.processEvents()
        
        # Summary of plugin loading
        if successfully_loaded:
            self.logger.info(f"Successfully loaded {len(successfully_loaded)} plugins: {', '.join(successfully_loaded)}")
        if failed_plugins:
            self.logger.warning(f"Failed to load {len(failed_plugins)} plugins: {', '.join(failed_plugins)}")
        
        return len(successfully_loaded) > 0  # Return True if at least one plugin was loaded
    
    def _load_plugin(self, plugin_name: str, plugin_dir: str):
        """Load a specific plugin."""
        main_file = os.path.join(plugin_dir, "main.py")
        if not os.path.exists(main_file):
            self.logger.warning(f"Plugin {plugin_name} has no main.py file")
            return
        
        try:
            # Create plugin API instance
            plugin_api = PluginAPI(self, plugin_name)
            
            # Load the plugin module
            spec = importlib.util.spec_from_file_location(
                f"plugins.{plugin_name}", main_file
            )
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            
            # Initialize plugin
            if hasattr(module, "PortScannerPlugin"):
                plugin = module.PortScannerPlugin(plugin_api)
                self.plugins[plugin_name] = plugin
                self.plugin_apis[plugin_name] = plugin_api
                self.logger.info(f"Loaded plugin: {plugin_name}")
            else:
                self.logger.warning(f"Plugin {plugin_name} has no PortScannerPlugin class")
        
        except Exception as e:
            self.logger.error(f"Error loading plugin {plugin_name}: {str(e)}")
    
    def get_ui_component(self, plugin_name: str, panel_name: str):
        """Get a UI component from a plugin for a specific panel."""
        plugin = self.plugins.get(plugin_name)
        if plugin and hasattr(plugin, "get_ui_component"):
            return plugin.get_ui_component(panel_name)
        return None
    
    def get_plugin_menu_items(self, selected_device=None, plugin_id=None) -> List[Dict]:
        """Get all menu items from all plugins, filtered by current context.
        
        Args:
            selected_device: Optional device data for context-specific menu items
            plugin_id: Optional ID to filter menu items for a specific plugin
            
        Returns:
            List of menu item dictionaries
        """
        menu_items = []
        
        if plugin_id:
            # Return menu items for a specific plugin only
            plugin_api = self.plugin_apis.get(plugin_id)
            if plugin_api and hasattr(plugin_api, '_menu_items'):
                return plugin_api._menu_items
            return []
        
        # Return menu items from all plugins
        for plugin_name, plugin_api in self.plugin_apis.items():
            if hasattr(plugin_api, '_menu_items'):
                for item in plugin_api._menu_items:
                    # Check if the item should be enabled
                    if item['enabled_callback']:
                        try:
                            enabled = item['enabled_callback'](selected_device)
                        except Exception as e:
                            self.logger.error(f"Error checking menu item enabled state: {str(e)}")
                            enabled = False
                    else:
                        enabled = True
                    
                    if enabled:
                        menu_items.append(item)
        
        return menu_items
    
    def refresh_menus(self):
        """Notify all registered menu callbacks that menus need to be refreshed."""
        self.logger.debug("Refreshing plugin menus")
        for callback in self.menu_callbacks:
            try:
                callback()
            except Exception as e:
                self.logger.error(f"Error in menu refresh callback: {str(e)}")
    
    def register_menu_callback(self, callback: Callable):
        """Register a callback to be notified when menus need to be refreshed."""
        self.logger.debug(f"Registering menu callback: {callback.__name__ if hasattr(callback, '__name__') else str(callback)}")
        if callback not in self.menu_callbacks:
            self.menu_callbacks.append(callback)
    
    def unregister_menu_callback(self, callback: Callable):
        """Unregister a menu callback."""
        self.logger.debug(f"Unregistering menu callback: {callback.__name__ if hasattr(callback, '__name__') else str(callback)}")
        if callback in self.menu_callbacks:
            self.menu_callbacks.remove(callback)

    def register_panel(self, panel, location, name=None):
        """Register a panel with the main window.
        
        Args:
            panel: The panel widget to register
            location: Where to place the panel ('left', 'right', or 'bottom')
            name: Optional name for the panel tab (only used for right panel)
        
        Returns:
            bool: True if registration was successful, False otherwise
        """
        try:
            # If main window is not available, queue the panel for later
            if not self.main_window:
                self.logger.info(f"Main window not available, queueing panel for {location}")
                self._pending_panels.append((panel, location, name))
                return True
            
            # Register panel with main window
            self.main_window.register_panel(panel, location, name)
            self.logger.info(f"Successfully registered panel at {location}: {name or 'unnamed'}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error registering panel: {str(e)}")
            return False

    def _create_plugin_api(self, plugin_id):
        """Create a plugin API instance for a plugin."""
        return PluginAPI(plugin_id, self)

    def register_menu_item(self, label, callback, enabled_callback=None, icon_path=None, shortcut=None, parent_menu=None):
        """Register a menu item for the plugin.
        
        Args:
            label: Text to show in the menu
            callback: Function to call when clicked
            enabled_callback: Function that returns bool to determine if item is enabled
            icon_path: Optional path to an icon
            shortcut: Optional keyboard shortcut
            parent_menu: Optional parent menu name
            
        Returns:
            bool: True if registration was successful
        """
        menu_item = {
            'plugin_id': self.plugin_id,
            'label': label,
            'callback': callback,
            'enabled_callback': enabled_callback,
            'icon_path': icon_path,
            'shortcut': shortcut,
            'parent_menu': parent_menu
        }
        self._menu_items.append(menu_item)
        
        # If we have a main window reference, update menus
        if self.main_window:
            self.main_window.refresh_menus()
        
        return True

    def get_plugin_config(self, plugin_id):
        """Get the configuration for a specific plugin.
        
        Args:
            plugin_id: The ID of the plugin
            
        Returns:
            dict: The plugin's configuration
        """
        if plugin_id not in self.config["plugins"]:
            return {}
        return self.config["plugins"][plugin_id].get("settings", {})

    def set_plugin_config(self, plugin_id, config):
        """Set the configuration for a specific plugin.
        
        Args:
            plugin_id: The ID of the plugin
            config: The configuration to set
            
        Returns:
            bool: True if successful
        """
        if plugin_id not in self.config["plugins"]:
            return False
            
        self.config["plugins"][plugin_id]["settings"] = config
        return self.save_config()

    def get_plugin_config_dialog(self, plugin_id):
        """Get a configuration dialog for a specific plugin.
        
        Args:
            plugin_id: The ID of the plugin
            
        Returns:
            QDialog: The configuration dialog, or None if not available
        """
        if plugin_id not in self.plugins:
            return None
            
        plugin_info = self.plugins[plugin_id]
        if not plugin_info["instance"]:
            return None
            
        # Check if plugin has a config panel
        if hasattr(plugin_info["instance"], "get_config_panel"):
            try:
                return plugin_info["instance"].get_config_panel()
            except Exception as e:
                self.logger.error(f"Error getting config panel for plugin {plugin_id}: {str(e)}")
                return None
                
        return None

    def set_main_window(self, main_window):
        """Set the main window reference.
        
        Args:
            main_window: The main window instance
        """
        self.main_window = main_window
        self.logger.debug("Main window reference set in plugin manager")
        
        # Set main window reference in all plugin APIs
        for plugin_id, plugin_api in self.plugin_apis.items():
            plugin_api.main_window = main_window
            self.logger.debug(f"Main window reference set in plugin API for {plugin_id}")
            
        # Note: workspace_manager is now handled by the core-workspace plugin
        # and is not set directly on plugin APIs

    def get_plugin_errors(self):
        """Get a dictionary of plugin errors.
        
        Returns:
            dict: Dictionary with plugin_id as key and error message as value
        """
        return self.plugin_errors
    
    def clear_plugin_errors(self, plugin_id=None):
        """Clear plugin errors.
        
        Args:
            plugin_id (str, optional): ID of the plugin to clear errors for.
                                      If None, clear all errors.
        """
        if plugin_id is None:
            self.plugin_errors.clear()
        elif plugin_id in self.plugin_errors:
            del self.plugin_errors[plugin_id]
            self.logger.info(f"Cleared errors for plugin: {plugin_id}")

class PluginAPI:
    """API provided to plugins for interacting with the application."""
    
    def __init__(self, plugin_id, plugin_manager):
        """Initialize plugin API.
        
        Args:
            plugin_id: ID of the plugin
            plugin_manager: Reference to plugin manager
        """
        self.plugin_id = plugin_id
        self._plugin_manager = plugin_manager
        self.main_window = None
        self._logger = logging.getLogger(f"plugin.{plugin_id}")
        
        # Store callbacks to be executed when main window is ready
        self.main_window_callbacks = []
        
        # Create event hooks for this plugin
        self.hook_callbacks = {}
        
        # Signal handlers
        self._main_window_ready_handlers = []
    
    def register_hook(self, hook_name, callback):
        """Register a hook for the plugin.
        
        Args:
            hook_name: Name of the hook
            callback: Callback function
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self._plugin_manager.register_hook(hook_name, self.plugin_id, callback)
        
    def hook(self, hook_name):
        """Decorator to register a hook callback.
        
        Args:
            hook_name: Name of the hook to register
            
        Returns:
            Decorator function
        """
        def decorator(callback):
            self._plugin_manager.register_hook(hook_name, self.plugin_id, callback)
            return callback
        return decorator
    
    def call_hook(self, hook_name, *args, **kwargs):
        """Call a registered hook.
        
        Args:
            hook_name: Name of the hook to call
            *args: Arguments to pass to the hook
            **kwargs: Keyword arguments to pass to the hook
        """
        return self._plugin_manager.trigger_hook(hook_name, *args, **kwargs)
    
    def register_function(self, function_name, callback):
        """Register a function for the plugin that can be called by other plugins.
        
        Args:
            function_name: Name of the function to register
            callback: Function to call
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not hasattr(self, "_exported_functions"):
            self._exported_functions = {}
        
        self._exported_functions[function_name] = callback
        return True
    
    def call_function(self, function_name, *args, **kwargs):
        """Call a registered function.
        
        Args:
            function_name: Name of the function to call
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            The return value of the function
        """
        if not hasattr(self, "_exported_functions") or function_name not in self._exported_functions:
            raise AttributeError(f"Function {function_name} not registered")
        
        return self._exported_functions[function_name](*args, **kwargs)
    
    def on_main_window_ready(self, callback):
        """Register a callback to be executed when the main window is ready.
        
        Args:
            callback: Function to call when main window is ready
        """
        if self.main_window is not None:
            # Main window is already ready, call immediately
            try:
                callback()
            except Exception as e:
                self._logger.error(f"Error in main window ready callback: {str(e)}")
        else:
            # Store callback for later execution
            self._main_window_ready_handlers.append(callback)
    
    def set_main_window(self, main_window):
        """Set the main window reference.
        
        This is called by the application when the main window is ready.
        
        Args:
            main_window: Reference to the main application window
        """
        try:
            # Store main window reference
            self.main_window = main_window
            
            # Execute all pending callbacks
            for callback in self._main_window_ready_handlers:
                try:
                    callback()
                except Exception as e:
                    import traceback
                    error_msg = f"Error in main window ready callback: {str(e)}\n{traceback.format_exc()}"
                    self._logger.error(error_msg)
                    # Store error in plugin_manager.plugin_errors
                    self._plugin_manager.plugin_errors[self.plugin_id] = error_msg
                    
            # Clear callbacks after execution
            self._main_window_ready_handlers = []
            
        except Exception as e:
            import traceback
            error_msg = f"Error setting main window: {str(e)}\n{traceback.format_exc()}"
            self._logger.error(error_msg)
            # Store error in plugin_manager.plugin_errors
            self._plugin_manager.plugin_errors[self.plugin_id] = error_msg
    
    def log(self, message, level="INFO"):
        """Log a message to the application log.
        
        Args:
            message: Message to log
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        level_num = getattr(logging, level.upper(), logging.INFO)
        self._logger.log(level_num, message)
    
    def send_message(self, target_plugin_id, message):
        """Send a message to another plugin."""
        return self._plugin_manager.send_message(target_plugin_id, message)
    
    def broadcast(self, message):
        """Broadcast a message to all plugins."""
        return self._plugin_manager.broadcast(message)
    
    def get_setting(self, key, default=None):
        """Get a plugin setting.
        
        Args:
            key: Setting key
            default: Default value if setting not found
            
        Returns:
            Setting value
        """
        plugin_config = self._plugin_manager.get_plugin_config(self.plugin_id)
        return plugin_config.get("settings", {}).get(key, default)
    
    def set_setting(self, key, value):
        """Set a plugin setting.
        
        Args:
            key: Setting key
            value: Setting value
            
        Returns:
            True if successful, False otherwise
        """
        plugin_config = self._plugin_manager.get_plugin_config(self.plugin_id)
        if "settings" not in plugin_config:
            plugin_config["settings"] = {}
        plugin_config["settings"][key] = value
        return self._plugin_manager.set_plugin_config(self.plugin_id, plugin_config)
    
    def register_menu_item(self, label, callback, enabled_callback=None, icon_path=None, shortcut=None, parent_menu=None):
        """Register a menu item.
        
        Args:
            label: Menu item label
            callback: Function to call when item is clicked
            enabled_callback: Function to determine if item is enabled
            icon_path: Path to menu item icon
            shortcut: Keyboard shortcut
            parent_menu: Parent menu name
            
        Returns:
            True if successful, False otherwise
        """
        # Use weakref to prevent circular references
        import weakref
        
        try:
            if self.main_window is None:
                self._logger.warning("Cannot register menu item: main window not available")
                # Schedule for when main window is ready
                self.on_main_window_ready(lambda: self.register_menu_item(
                    label, callback, enabled_callback, icon_path, shortcut, parent_menu
                ))
                return False
            
            # Register menu item with main window
            return self._plugin_manager.register_menu_item(
                label=label,
                callback=callback,
                enabled_callback=enabled_callback,
                icon_path=icon_path,
                shortcut=shortcut,
                parent_menu=parent_menu
            )
        except Exception as e:
            self._logger.error(f"Error registering menu item: {str(e)}")
            return False
    
    def get_menu_items(self) -> List[Dict]:
        """Get all registered menu items for this plugin."""
        # Return the items directly to avoid circular calls
        return self._menu_items
    
    def register_toolbar(self, toolbar, category="Tools"):
        """Register a toolbar.
        
        Args:
            toolbar: Toolbar widget
            category: Toolbar category
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.main_window is None:
                self._logger.warning("Cannot register toolbar: main window not available")
                # Schedule for when main window is ready
                self.on_main_window_ready(lambda: self.register_toolbar(toolbar, category))
                return False
            
            # Register toolbar with main window
            self.main_window.add_toolbar_widget(toolbar, category)
            return True
        except Exception as e:
            self._logger.error(f"Error registering toolbar: {str(e)}")
            return False
    
    def register_panel(self, panel, location, name=None):
        """Register a panel.
        
        Args:
            panel: Panel widget
            location: Panel location (left, right, bottom)
            name: Panel name
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.main_window is None:
                self._logger.warning("Cannot register panel: main window not available")
                # Schedule for when main window is ready
                self.on_main_window_ready(lambda: self.register_panel(panel, location, name))
                return False
                
            # Set panel name if provided
            if name:
                panel.setObjectName(name)
                
            # Set plugin ID on panel
            panel.setProperty("plugin_id", self.plugin_id)
            
            # Thread safety: ensure panel is owned by the main window thread before registration
            from PySide6.QtCore import QCoreApplication
            main_thread = self.main_window.thread()
            if panel.thread() != main_thread:
                self._logger.debug(f"Moving panel {name} to main thread for proper rendering")
                panel.moveToThread(main_thread)
                
            # Register panel with main window
            self.main_window.register_panel(panel, location, name)
            return True
        except Exception as e:
            self._logger.error(f"Error registering panel: {str(e)}")
            return False
    
    def add_tab(self, widget, title, icon_path=None):
        """Add a tab to the bottom panel.
        
        Args:
            widget: Tab widget
            title: Tab title
            icon_path: Path to tab icon
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.main_window is None:
                self._logger.warning("Cannot add tab: main window not available")
                # Schedule for when main window is ready
                self.on_main_window_ready(lambda: self.add_tab(widget, title, icon_path))
                return False
                
            # Set plugin ID on widget
            widget.setProperty("plugin_id", self.plugin_id)
            
            try:
                # Get bottom panel
                bottom_panel = self.main_window.bottom_panel
                
                # Create icon if path provided
                icon = None
                if icon_path and os.path.exists(icon_path):
                    from PySide6.QtGui import QIcon
                    icon = QIcon(icon_path)
                
                # Add tab to bottom panel
                if icon:
                    bottom_panel.addTab(widget, icon, title)
                else:
                    bottom_panel.addTab(widget, title)
                
                return True
            except Exception as e:
                self._logger.error(f"Error adding tab: {str(e)}")
                return False
        except Exception as e:
            self._logger.error(f"Error adding tab: {str(e)}")
            return False
    
    def remove_tab(self, title):
        """Remove a tab from the bottom panel.
        
        Args:
            title: Tab title
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.main_window is None:
                self._logger.warning("Cannot remove tab: main window not available")
                return False
                
            try:
                # Get bottom panel
                bottom_panel = self.main_window.bottom_panel
                
                # Find tab by title
                for i in range(bottom_panel.count()):
                    if bottom_panel.tabText(i) == title:
                        # Check if tab belongs to this plugin
                        widget = bottom_panel.widget(i)
                        plugin_id = widget.property("plugin_id")
                        if plugin_id == self.plugin_id:
                            # Remove tab
                            bottom_panel.removeTab(i)
                            return True
                
                return False
            except Exception as e:
                self._logger.error(f"Error removing tab: {str(e)}")
                return False
        except Exception as e:
            self._logger.error(f"Error removing tab: {str(e)}")
            return False
    
    def get_network_interfaces(self):
        """Get list of network interfaces.
        
        Returns:
            List of network interfaces
        """
        try:
            # Use core-workspace plugin instead of direct workspace manager
            if self._plugin_manager:
                workspace_plugin_api = self._plugin_manager.plugin_apis.get("core-workspace")
                if workspace_plugin_api:
                    # This functionality may be provided by a different plugin
                    # For now, return empty list if not available
                    return []
            return []
        except Exception as e:
            self._logger.error(f"Error getting network interfaces: {str(e)}")
            return []
    
    def get_current_device(self):
        """Get currently selected device.
        
        Returns:
            Selected device or None if none selected
        """
        try:
            # Safely get current device through main window
            if self.main_window and self.main_window.device_table:
                return self.main_window.device_table.get_selected_device()
            return None
        except Exception as e:
            self._logger.error(f"Error getting current device: {str(e)}")
            return None
    
    def get_current_workspace(self):
        """Get current workspace.
        
        Returns:
            Current workspace or None if none loaded
        """
        try:
            # Use core-workspace plugin instead of direct workspace manager
            if self._plugin_manager:
                workspace_plugin_api = self._plugin_manager.plugin_apis.get("core-workspace")
                if workspace_plugin_api:
                    return workspace_plugin_api.call_function("get_current_workspace")
            return None
        except Exception as e:
            self._logger.error(f"Error getting current workspace: {str(e)}")
            return None
    
    def show_progress(self, show=True):
        """Show or hide progress bar.
        
        Args:
            show: True to show, False to hide
        """
        try:
            # Safely show/hide progress bar through main window
            if self.main_window:
                self.main_window.show_progress(show)
        except Exception as e:
            self._logger.error(f"Error showing progress: {str(e)}")
    
    def update_progress(self, value, maximum=100):
        """Update progress bar value.
        
        Args:
            value: Progress value
            maximum: Progress maximum value
        """
        try:
            # Safely update progress bar through main window
            if self.main_window:
                self.main_window.update_progress(value, maximum)
        except Exception as e:
            self._logger.error(f"Error updating progress: {str(e)}")
    
    def add_console_message(self, message, level="INFO"):
        """Add a message to the console.
        
        Args:
            message: Message to add
            level: Message level
        """
        # Log messages go to the console through the logging system
        self._logger.log(level, message)
    
    def cleanup(self):
        """Clean up plugin API resources."""
        try:
            # Clear references to prevent memory leaks
            self.main_window = None
            # Remove workspace_manager reference as it's now handled by core-workspace plugin
            self._main_window_ready_handlers = []
            self.hook_callbacks = {}
        except Exception as e:
            self._logger.error(f"Error during cleanup: {str(e)}") 