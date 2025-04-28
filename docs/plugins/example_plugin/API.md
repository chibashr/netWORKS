# Example Plugin API Documentation

## Version
1.0.0

## Overview
This document describes the API provided by the Example Plugin for use by other plugins.

## Exported Functions

### ping_device(ip_address)
**Description:** Pings the specified IP address and returns the results  
**Parameters:**
- `ip_address` (str): The IP address to ping
**Returns:** Dictionary with ping results:
```python
{
    "success": True,  # Whether the ping was successful
    "times": [24, 35, 28, 30],  # Response times in ms
    "sent": 4,  # Number of packets sent
    "received": 4,  # Number of packets received
    "loss": 0.0,  # Packet loss percentage
    "min": 24,  # Minimum response time (ms)
    "avg": 29.25,  # Average response time (ms)
    "max": 35  # Maximum response time (ms)
}
```
**Example:**
```python
result = plugin_api.call_plugin_function("example-plugin", "ping_device", "192.168.1.1")
if result["success"]:
    print(f"Ping successful! Average time: {result['avg']}ms")
```

### get_device_info(ip_address)
**Description:** Retrieves detailed information about a device  
**Parameters:**
- `ip_address` (str): The IP address of the device
**Returns:** Dictionary with device information:
```python
{
    "ip": "192.168.1.1",
    "hostname": "router.local",
    "mac": "00:11:22:33:44:55",
    "vendor": "Cisco Systems",
    "os": "IOS",
    "uptime": "14 days, 3 hours",
    "ports": [22, 80, 443]
}
```
**Example:**
```python
device_info = plugin_api.call_plugin_function("example-plugin", "get_device_info", "192.168.1.1")
print(f"Device hostname: {device_info['hostname']}")
```

## Events/Hooks

### example:device_pinged
**Description:** Triggered when a device is pinged by the plugin  
**Data Structure:**
```python
{
    "ip": "192.168.1.1",  # IP address of the pinged device
    "success": True,  # Whether the ping was successful
    "timestamp": "2023-08-01T12:34:56",  # ISO format timestamp
    "response_time": 29.25  # Average response time in ms
}
```
**Example Usage:**
```python
@plugin_api.hook("example:device_pinged")
def on_device_pinged(data):
    if data["success"]:
        plugin_api.log(f"Device {data['ip']} responded in {data['response_time']}ms")
    else:
        plugin_api.log(f"Device {data['ip']} did not respond")
```

### example:device_info_retrieved
**Description:** Triggered when device information is retrieved  
**Data Structure:**
```python
{
    "ip": "192.168.1.1",  # IP address of the device
    "timestamp": "2023-08-01T12:34:56",  # ISO format timestamp
    "info": {  # Device information
        # Device info dictionary as returned by get_device_info
    }
}
```
**Example Usage:**
```python
@plugin_api.hook("example:device_info_retrieved")
def on_device_info(data):
    device_info = data["info"]
    plugin_api.log(f"Retrieved info for {device_info['hostname']} ({data['ip']})")
```

## Data Structures

### DeviceInfo
**Description:** Represents information about a network device  
**Fields:**
- `ip` (str): IP address of the device
- `hostname` (str): Hostname of the device
- `mac` (str): MAC address of the device
- `vendor` (str): Vendor/manufacturer name
- `os` (str, optional): Operating system if detected
- `uptime` (str, optional): Device uptime if available
- `ports` (list, optional): List of open ports

### PingResult
**Description:** Represents results from a ping operation  
**Fields:**
- `success` (bool): Whether the ping was successful
- `times` (list): List of response times for each packet
- `sent` (int): Number of packets sent
- `received` (int): Number of packets received
- `loss` (float): Packet loss percentage
- `min` (float): Minimum response time in ms
- `avg` (float): Average response time in ms
- `max` (float): Maximum response time in ms

## Integration Examples

### Simple Integration
```python
def init_plugin(plugin_api):
    # Register for device pinged events
    @plugin_api.hook("example:device_pinged")
    def on_device_pinged(data):
        plugin_api.log(f"Device {data['ip']} pinged with result: {data['success']}")
    
    # Register menu item to ping a device
    plugin_api.register_menu_item(
        label="Ping Current Device with Example Plugin",
        callback=ping_current_device,
        enabled_callback=lambda device: device is not None,
        parent_menu="Tools"
    )
    
    def ping_current_device():
        device = plugin_api.get_current_device()
        if device:
            result = plugin_api.call_plugin_function("example-plugin", "ping_device", device["ip"])
            if result["success"]:
                plugin_api.log(f"Ping successful! Average time: {result['avg']}ms")
            else:
                plugin_api.log(f"Ping failed!")

    return YourPlugin(plugin_api)
```

## Version History

### v1.0.0 (Initial Release)
- Basic device ping functionality
- Device information retrieval
- Events for device operations 