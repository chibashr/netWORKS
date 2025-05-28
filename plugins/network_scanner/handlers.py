"""
Event Handlers Module

This module contains all the event handlers for the network scanner plugin.
"""

from loguru import logger
from typing import Any, List, Optional
from PySide6.QtWidgets import QMessageBox, QInputDialog, QLineEdit

def on_scan_button_clicked(plugin: Any) -> None:
    """Handle scan button click"""
    try:
        # Get network range from UI
        if not plugin.network_range_edit:
            logger.error("Network range edit field not available")
            return
            
        network_range = plugin.network_range_edit.text().strip()
        if not network_range:
            QMessageBox.warning(
                plugin.main_window,
                "Warning",
                "Please enter a network range to scan"
            )
            return
            
        # Get scan type from UI
        scan_type = plugin.scan_type_combo.currentText() if plugin.scan_type_combo else "Quick Scan"
        
        # Start the scan
        plugin.scan_network(network_range, scan_type)
        
    except Exception as e:
        logger.error(f"Error in scan button handler: {e}")
        QMessageBox.critical(
            plugin.main_window,
            "Error",
            f"An error occurred while starting the scan: {str(e)}"
        )

def on_stop_button_clicked(plugin: Any) -> None:
    """Handle stop button click"""
    try:
        plugin.stop_scan()
    except Exception as e:
        logger.error(f"Error stopping scan: {e}")
        QMessageBox.critical(
            plugin.main_window,
            "Error",
            f"An error occurred while stopping the scan: {str(e)}"
        )

def on_quick_ping_button_clicked(plugin: Any) -> None:
    """Handle quick ping button click"""
    try:
        # Get network range from UI
        if not plugin.network_range_edit:
            logger.error("Network range edit field not available")
            return
            
        network_range = plugin.network_range_edit.text().strip()
        if not network_range:
            QMessageBox.warning(
                plugin.main_window,
                "Warning",
                "Please enter a network range to scan"
            )
            return
            
        # Start a quick ping scan
        plugin.scan_network(network_range, "Quick Scan (ping only)")
        
    except Exception as e:
        logger.error(f"Error in quick ping handler: {e}")
        QMessageBox.critical(
            plugin.main_window,
            "Error",
            f"An error occurred during quick ping scan: {str(e)}"
        )

def on_scan_action(plugin: Any) -> None:
    """Handle scan action from menu/toolbar"""
    try:
        # Show the scanner dock widget
        for dock in plugin.main_window.findChildren(QDockWidget):
            if dock.objectName() == "NetworkScannerDock":
                dock.show()
                dock.raise_()
                break
                
        # Focus the network range field
        if plugin.network_range_edit:
            plugin.network_range_edit.setFocus()
            
    except Exception as e:
        logger.error(f"Error in scan action handler: {e}")

def on_scan_selected_action(plugin: Any) -> None:
    """Handle scan from selected device action"""
    try:
        # Get selected devices
        selected_devices = plugin.main_window.get_selected_devices()
        if not selected_devices:
            QMessageBox.warning(
                plugin.main_window,
                "Warning",
                "Please select a device to scan from"
            )
            return
            
        # Use the first selected device
        device = selected_devices[0]
        ip_address = device.get_property('ip_address')
        if not ip_address:
            QMessageBox.warning(
                plugin.main_window,
                "Warning",
                "Selected device has no IP address"
            )
            return
            
        # Show the scanner dock widget
        for dock in plugin.main_window.findChildren(QDockWidget):
            if dock.objectName() == "NetworkScannerDock":
                dock.show()
                dock.raise_()
                break
                
        # Set the network range to the device's subnet
        if plugin.network_range_edit:
            from plugins.network_scanner.utils import get_subnet_for_ip
            subnet = get_subnet_for_ip(ip_address)
            plugin.network_range_edit.setText(subnet)
            
    except Exception as e:
        logger.error(f"Error in scan selected action handler: {e}")

def on_scan_type_manager_action(plugin: Any) -> None:
    """Handle scan type manager action"""
    try:
        # Import the comprehensive scan type manager dialog
        from plugins.network_scanner.ui import create_scan_type_manager_dialog
        
        # Create and show the dialog, passing the plugin instance
        dialog_components = create_scan_type_manager_dialog(plugin.main_window, plugin._settings, plugin)
        dialog = dialog_components['dialog']
        
        # Show the dialog
        dialog.exec()
        
        # After dialog closes, update all dropdowns to reflect any changes
        plugin._update_all_scan_type_dropdowns()
        
    except Exception as e:
        logger.error(f"Error in scan type manager action handler: {e}")
        import traceback
        traceback.print_exc()

def _on_scan_network_action(plugin: Any, selected_items: List[Any]) -> None:
    """Handle scan network context menu action"""
    try:
        # Show input dialog for network range
        network_range, ok = QInputDialog.getText(
            plugin.main_window,
            "Scan Network",
            "Enter network range to scan (e.g. 192.168.1.0/24):",
            QLineEdit.Normal,
            ""
        )
        
        if ok and network_range:
            # Show the scanner dock widget
            for dock in plugin.main_window.findChildren(QDockWidget):
                if dock.objectName() == "NetworkScannerDock":
                    dock.show()
                    dock.raise_()
                    break
                    
            # Set the network range and start scan
            if plugin.network_range_edit:
                plugin.network_range_edit.setText(network_range)
                plugin.scan_network(network_range)
                
    except Exception as e:
        logger.error(f"Error in scan network action handler: {e}")

def _on_scan_subnet_action(plugin: Any, selected_items: List[Any]) -> None:
    """Handle scan subnet context menu action"""
    try:
        # Get selected devices
        selected_devices = plugin.main_window.get_selected_devices()
        if not selected_devices:
            return
            
        # Use the first selected device
        device = selected_devices[0]
        ip_address = device.get_property('ip_address')
        if not ip_address:
            return
            
        # Get subnet for the IP
        from plugins.network_scanner.utils import get_subnet_for_ip
        subnet = get_subnet_for_ip(ip_address)
        
        # Show the scanner dock widget
        for dock in plugin.main_window.findChildren(QDockWidget):
            if dock.objectName() == "NetworkScannerDock":
                dock.show()
                dock.raise_()
                break
                
        # Set the network range and start scan
        if plugin.network_range_edit:
            plugin.network_range_edit.setText(subnet)
            plugin.scan_network(subnet)
            
    except Exception as e:
        logger.error(f"Error in scan subnet action handler: {e}")

def _on_scan_from_device_action(plugin: Any, selected_items: List[Any]) -> None:
    """Handle scan from device context menu action"""
    try:
        # Get selected devices
        selected_devices = plugin.main_window.get_selected_devices()
        if not selected_devices:
            return
            
        # Use the first selected device
        device = selected_devices[0]
        ip_address = device.get_property('ip_address')
        if not ip_address:
            return
            
        # Show input dialog for network range
        network_range, ok = QInputDialog.getText(
            plugin.main_window,
            "Scan from Device",
            "Enter network range to scan:",
            QLineEdit.Normal,
            ip_address
        )
        
        if ok and network_range:
            # Show the scanner dock widget
            for dock in plugin.main_window.findChildren(QDockWidget):
                if dock.objectName() == "NetworkScannerDock":
                    dock.show()
                    dock.raise_()
                    break
                    
            # Set the network range and start scan
            if plugin.network_range_edit:
                plugin.network_range_edit.setText(network_range)
                plugin.scan_network(network_range)
                
    except Exception as e:
        logger.error(f"Error in scan from device action handler: {e}")

def _on_rescan_device_action(plugin: Any, selected_items: List[Any]) -> None:
    """Handle rescan device context menu action"""
    try:
        # Get selected devices
        selected_devices = plugin.main_window.get_selected_devices()
        if not selected_devices:
            return
            
        # Scan each selected device that has an IP
        for device in selected_devices:
            ip_address = device.get_property('ip_address')
            if ip_address:
                plugin.scan_network(ip_address)
                
    except Exception as e:
        logger.error(f"Error in rescan device action handler: {e}") 