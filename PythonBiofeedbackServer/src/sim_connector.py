#!/usr/bin/env python3
"""
Simulator Connector Implementation
==================================

Wraps the existing sensors.py simulation functions into the SensorConnector interface.
This allows the current simulator to work with the new abstraction layer.
"""

from typing import Dict
from connectors import SensorConnector
from sensors import get_hr, get_eda, get_hrv

class SimConnector(SensorConnector):
    """
    Simulator implementation of SensorConnector.
    
    Uses the existing sensors.py simulation functions to provide
    realistic biofeedback data for testing and demonstration.
    """
    
    def __init__(self):
        """Initialize the simulator connector."""
        self._connected = True
    
    def read(self) -> Dict[str, float]:
        """
        Read simulated sensor values from sensors.py functions.
        
        Returns:
            Dictionary with 'hr', 'eda', 'hrv' keys and simulated values
        """
        if not self._connected:
            raise RuntimeError("Simulator connector is not connected")
        
        return {
            "hr": get_hr(),
            "eda": get_eda(), 
            "hrv": get_hrv()
        }
    
    def close(self) -> None:
        """
        Close the simulator connection.
        """
        self._connected = False
    
    def is_connected(self) -> bool:
        """
        Check if simulator is connected.
        
        Returns:
            True if simulator is active, False otherwise
        """
        return self._connected
    
    def get_info(self) -> Dict[str, str]:
        """
        Get simulator connector information.
        
        Returns:
            Dictionary with connector details
        """
        base_info = super().get_info()
        base_info.update({
            "description": "Biofeedback simulation using sensors.py",
            "data_source": "Mathematical simulation with realistic physiological parameters"
        })
        return base_info
