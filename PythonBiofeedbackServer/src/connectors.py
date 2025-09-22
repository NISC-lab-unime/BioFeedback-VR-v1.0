#!/usr/bin/env python3
"""
Sensor Connector Abstraction
============================

Abstract base class for biofeedback sensor connections.
Provides a common interface for different sensor types (simulator, BLE, LSL, vendor SDKs).

This abstraction allows the server to work with any sensor implementation
without changing the core server logic.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional

class SensorConnector(ABC):
    """
    Abstract base class for biofeedback sensor connections.
    
    All sensor implementations must inherit from this class and implement
    the required methods for reading sensor data and cleanup.
    """
    
    @abstractmethod
    def read(self) -> Dict[str, float]:
        """
        Read current sensor values.
        
        Returns:
            Dictionary with at least 'hr', 'eda', 'hrv' keys and float values
        """
        pass
    
    @abstractmethod
    def close(self) -> None:
        """
        Clean up sensor resources and close connections.
        """
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if the sensor connection is active.
        
        Returns:
            True if connected and ready to read data, False otherwise
        """
        pass
    
    def get_info(self) -> Dict[str, str]:
        """
        Get sensor connector information.
        
        Returns:
            Dictionary with connector type and status information
        """
        return {
            "type": self.__class__.__name__,
            "connected": str(self.is_connected())
        }
