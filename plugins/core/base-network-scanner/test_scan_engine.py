import sys
from scan_engine import NetworkScanner

scanner = NetworkScanner(None)
ip_list = scanner._parse_ip_range('10.1.8.1-254')
print(f'Parsed {len(ip_list)} IPs')
print(f'First few IPs: {ip_list[:5]}') 