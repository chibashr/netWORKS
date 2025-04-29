#!/usr/bin/env python3
# netWORKS - Database Models

import uuid
import json
import datetime
from typing import Dict, List, Any, Optional, Union


class BaseModel:
    """Base class for all database models with common functionality."""
    
    def __init__(self, **kwargs):
        """Initialize the model with attributes."""
        self._attributes = {}
        self.update_attributes(kwargs)
    
    def update_attributes(self, attrs: Dict[str, Any]) -> None:
        """Update model attributes.
        
        Args:
            attrs: Dictionary of attributes to update
        """
        for key, value in attrs.items():
            if key.startswith('_'):
                continue  # Skip private attributes
            self._attributes[key] = value
    
    def get_attribute(self, key: str, default: Any = None) -> Any:
        """Get an attribute value.
        
        Args:
            key: Attribute name
            default: Default value if attribute doesn't exist
            
        Returns:
            The attribute value or default
        """
        return self._attributes.get(key, default)
    
    def set_attribute(self, key: str, value: Any) -> None:
        """Set an attribute value.
        
        Args:
            key: Attribute name
            value: Attribute value
        """
        self._attributes[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary.
        
        Returns:
            Dictionary representation of the model
        """
        return self._attributes.copy()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseModel':
        """Create model from dictionary.
        
        Args:
            data: Dictionary with model attributes
            
        Returns:
            An instance of the model
        """
        return cls(**data)


class Device(BaseModel):
    """Model representing a network device."""
    
    def __init__(self, **kwargs):
        """Initialize a device with default values and provided attributes.
        
        Args:
            **kwargs: Device attributes
        """
        # Ensure ID is present
        if 'id' not in kwargs:
            kwargs['id'] = str(uuid.uuid4())
        
        # Set default values if not provided
        now = datetime.datetime.now().isoformat()
        if 'first_seen' not in kwargs:
            kwargs['first_seen'] = now
        if 'last_seen' not in kwargs:
            kwargs['last_seen'] = now
        if 'status' not in kwargs:
            kwargs['status'] = 'active'
        if 'metadata' not in kwargs or not isinstance(kwargs['metadata'], dict):
            kwargs['metadata'] = {}
        if 'tags' not in kwargs:
            kwargs['tags'] = []
        
        super().__init__(**kwargs)
    
    @property
    def id(self) -> str:
        """Get device ID."""
        return self.get_attribute('id')
    
    @property
    def ip(self) -> Optional[str]:
        """Get device IP address."""
        return self.get_attribute('ip')
    
    @ip.setter
    def ip(self, value: str) -> None:
        """Set device IP address."""
        self.set_attribute('ip', value)
    
    @property
    def mac(self) -> Optional[str]:
        """Get device MAC address."""
        return self.get_attribute('mac')
    
    @mac.setter
    def mac(self, value: str) -> None:
        """Set device MAC address."""
        self.set_attribute('mac', value)
    
    @property
    def hostname(self) -> Optional[str]:
        """Get device hostname."""
        return self.get_attribute('hostname')
    
    @hostname.setter
    def hostname(self, value: str) -> None:
        """Set device hostname."""
        self.set_attribute('hostname', value)
    
    @property
    def vendor(self) -> Optional[str]:
        """Get device vendor."""
        return self.get_attribute('vendor')
    
    @vendor.setter
    def vendor(self, value: str) -> None:
        """Set device vendor."""
        self.set_attribute('vendor', value)
    
    @property
    def os(self) -> Optional[str]:
        """Get device operating system."""
        return self.get_attribute('os')
    
    @os.setter
    def os(self, value: str) -> None:
        """Set device operating system."""
        self.set_attribute('os', value)
    
    @property
    def status(self) -> str:
        """Get device status."""
        return self.get_attribute('status', 'active')
    
    @status.setter
    def status(self, value: str) -> None:
        """Set device status."""
        self.set_attribute('status', value)
    
    @property
    def first_seen(self) -> str:
        """Get device first seen timestamp."""
        return self.get_attribute('first_seen')
    
    @property
    def last_seen(self) -> str:
        """Get device last seen timestamp."""
        return self.get_attribute('last_seen')
    
    @last_seen.setter
    def last_seen(self, value: str) -> None:
        """Set device last seen timestamp."""
        self.set_attribute('last_seen', value)
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """Get device metadata."""
        return self.get_attribute('metadata', {})
    
    def set_metadata(self, key: str, value: Any) -> None:
        """Set a metadata value.
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        metadata = self.metadata
        metadata[key] = value
        self.set_attribute('metadata', metadata)
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get a metadata value.
        
        Args:
            key: Metadata key
            default: Default value if key doesn't exist
            
        Returns:
            The metadata value or default
        """
        return self.metadata.get(key, default)
    
    @property
    def tags(self) -> List[str]:
        """Get device tags."""
        return self.get_attribute('tags', [])
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the device.
        
        Args:
            tag: Tag to add
        """
        tags = self.tags
        if tag not in tags:
            tags.append(tag)
            self.set_attribute('tags', tags)
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the device.
        
        Args:
            tag: Tag to remove
        """
        tags = self.tags
        if tag in tags:
            tags.remove(tag)
            self.set_attribute('tags', tags)


class DeviceHistory(BaseModel):
    """Model representing a device history event."""
    
    def __init__(self, **kwargs):
        """Initialize a device history event.
        
        Args:
            **kwargs: Event attributes
        """
        # Set default values if not provided
        if 'timestamp' not in kwargs:
            kwargs['timestamp'] = datetime.datetime.now().isoformat()
        if 'event_data' not in kwargs:
            kwargs['event_data'] = {}
        
        super().__init__(**kwargs)
    
    @property
    def device_id(self) -> str:
        """Get the device ID."""
        return self.get_attribute('device_id')
    
    @property
    def ip(self) -> str:
        """Get the device IP."""
        return self.get_attribute('ip')
    
    @property
    def event_type(self) -> str:
        """Get the event type."""
        return self.get_attribute('event_type')
    
    @property
    def event_data(self) -> Dict[str, Any]:
        """Get the event data."""
        return self.get_attribute('event_data', {})
    
    @property
    def timestamp(self) -> str:
        """Get the event timestamp."""
        return self.get_attribute('timestamp')


class PluginData(BaseModel):
    """Model representing plugin-specific data."""
    
    def __init__(self, **kwargs):
        """Initialize plugin data.
        
        Args:
            **kwargs: Plugin data attributes
        """
        super().__init__(**kwargs)
    
    @property
    def plugin_id(self) -> str:
        """Get the plugin ID."""
        return self.get_attribute('plugin_id')
    
    @property
    def key(self) -> str:
        """Get the data key."""
        return self.get_attribute('key')
    
    @property
    def value(self) -> Any:
        """Get the data value."""
        return self.get_attribute('value')
    
    @value.setter
    def value(self, value: Any) -> None:
        """Set the data value."""
        self.set_attribute('value', value) 