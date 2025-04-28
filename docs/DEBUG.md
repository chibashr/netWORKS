# netWORKS Debugging Guide

## Common Issues and Solutions

### Network Interface Issues

#### No Network Interfaces Found
**Symptoms:**
- No interfaces appear in the interface dropdown
- Warning message: "No network interfaces found with IPv4 addresses"

**Solutions:**
1. Check if running with administrator privileges
2. Verify network adapter is enabled
3. Ensure IPv4 is configured on the interface
4. Check Windows Firewall settings

**Debug Steps:**
```python
# Add to refresh_interfaces method:
self.plugin.api.log(f"Available interfaces: {scapy.conf.ifaces.data}", "DEBUG")
```

### ARP Scan Issues

#### ARP Scan Failing
**Symptoms:**
- ARP scan returns no results
- Error: "Invalid interface" or "No MAC address found"

**Solutions:**
1. Verify interface name matches exactly
2. Check if running with administrator privileges
3. Ensure network adapter supports ARP
4. Verify network connectivity

**Debug Steps:**
```python
# Add to _arp_scan method:
self.plugin.api.log(f"Interface details: {netifaces.ifaddresses(interface)}", "DEBUG")
self.plugin.api.log(f"Scapy interface: {scapy.conf.iface}", "DEBUG")
```

### Port Scan Issues

#### Port Scan Timeouts
**Symptoms:**
- Port scans taking too long
- No results from TCP/UDP scans

**Solutions:**
1. Adjust timeout value in settings
2. Check firewall settings
3. Verify network connectivity
4. Reduce number of threads

**Debug Steps:**
```python
# Add to _tcp_scan and _udp_scan methods:
self.plugin.api.log(f"Scanning port {port} on {ip}", "DEBUG")
```

### DNS Resolution Issues

#### Hostname Resolution Failing
**Symptoms:**
- Hostnames not resolving
- DNS server errors

**Solutions:**
1. Check DNS server settings
2. Verify network connectivity
3. Try alternative DNS servers
4. Check DNS cache

**Debug Steps:**
```python
# Add to _scan_single_ip method:
self.plugin.api.log(f"DNS resolution attempt for {ip}", "DEBUG")
```

### Database Issues

#### Database Connection Issues
**Symptoms:**
- Error: "Unable to connect to database"
- Device data not loading or saving
- Application crashes when accessing data

**Solutions:**
1. Check if database file exists in the data directory
2. Verify that the application has write permissions to the data directory
3. Check for database file corruption
4. Restart the application to reset database connections

**Debug Steps:**
```python
# Add to database manager methods:
self.plugin.api.log(f"Database connection attempt: {db_path}", "DEBUG")
self.plugin.api.log(f"Database error details: {e}", "ERROR")
```

#### Data Persistence Issues
**Symptoms:**
- Device data not being saved between sessions
- Scan results disappearing after application restart
- Changes to device metadata not persisting

**Solutions:**
1. Check database write permissions
2. Verify database transactions are being committed
3. Ensure proper connection cleanup
4. Check for disk space issues

**Debug Steps:**
```python
# Add to save methods:
self.plugin.api.log(f"Saving data to database: {len(devices)} devices", "DEBUG")
self.plugin.api.log(f"Transaction commit result: {result}", "DEBUG")
```

### Performance Issues

#### Slow Scanning
**Symptoms:**
- Scans taking longer than expected
- UI becoming unresponsive

**Solutions:**
1. Reduce number of threads
2. Adjust timeout values
3. Limit port range
4. Disable unnecessary scan methods

**Debug Steps:**
```python
# Add to _scan_thread method:
self.plugin.api.log(f"Thread pool size: {scan_options['threads']}", "DEBUG")
self.plugin.api.log(f"Total IPs to scan: {len(ip_range)}", "DEBUG")
```

### UI Issues

#### Settings Panel Not Responding
**Symptoms:**
- Settings changes not taking effect
- Invalid input not showing warnings

**Solutions:**
1. Check signal connections
2. Verify validation methods
3. Ensure proper event handling
4. Check for UI thread issues

**Debug Steps:**
```python
# Add to settings panel methods:
self.plugin.api.log(f"Settings changed: {method} = {state}", "DEBUG")
```

## Logging Levels

The application uses the following logging levels:
- DEBUG: Detailed information for debugging
- INFO: General information about program execution
- WARNING: Indicate a potential problem
- ERROR: A more serious problem

## Debug Mode

To enable debug mode, set the environment variable:
```bash
export NETSCAN_DEBUG=1
```

## Common Error Messages

1. "Invalid interface":
   - Check if interface exists
   - Verify interface name format
   - Ensure proper permissions

2. "No MAC address found":
   - Check network adapter status
   - Verify IPv4 configuration
   - Check administrator privileges

3. "Port scan timeout":
   - Adjust timeout settings
   - Check firewall rules
   - Verify network connectivity

4. "DNS resolution failed":
   - Check DNS server settings
   - Verify network connectivity
   - Try alternative DNS servers

5. "Database connection error":
   - Verify database file exists
   - Check file permissions
   - Ensure adequate disk space
   - Check for database corruption

## Performance Optimization

1. Thread Management:
   - Default: 10 threads
   - Recommended range: 5-20
   - Adjust based on system resources

2. Timeout Settings:
   - Default: 2 seconds
   - Recommended range: 1-5 seconds
   - Longer timeouts = more accurate but slower

3. Port Range:
   - Default: 1-1024
   - Custom ranges supported
   - Smaller ranges = faster scans

4. Database Operations:
   - Use batch operations for better performance
   - Regular database maintenance improves speed
   - Consider periodic database vacuuming

## Network Requirements

1. Administrator Privileges:
   - Required for ARP scanning
   - Required for raw socket operations
   - Required for interface access

2. Network Access:
   - Local network access required
   - Firewall may block some operations
   - VPN may interfere with scanning

3. System Requirements:
   - Windows 10/11 or Linux
   - Python 3.8+
   - Network adapter with IPv4 support
   - Minimum 100MB disk space for database 