#!/usr/bin/env python3
"""
Biofeedback WebSocket Server
============================

Real-time streaming server for HR, EDA, and stress index data over WebSockets.
Provides both single-shot and continuous streaming endpoints for Unity integration.

Endpoints:
- "once": Single HR/EDA/stress sample
- "subscribe": Continuous streaming at ~10Hz

Based on research from:
- Lucifora et al. (2021) - Cyber-Therapy with biofeedback signals
- Moldoveanu et al. (2023) - Immersive Phobia Therapy through Adaptive VR
  
Date: August 2025
"""

import asyncio
import json
import logging
import signal
import sys
import time
from datetime import datetime, timezone
from typing import Set, Dict, Optional
import websockets

from sensors import (
    compute_stress_index, 
    get_current_scenario, _advance_time, get_current_time, set_scenario,
    should_collect_baseline_sample, collect_baseline_sample, compute_baseline_values,
    get_baseline_status, is_baseline_protocol_complete, reset_baseline_protocol
)
from sim_connector import SimConnector
from connectors import SensorConnector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BiofeedbackServer:
    """
    WebSocket server for real-time biofeedback streaming.
    
    Provides JSON-based endpoints for Unity and other clients to receive
    live HR, EDA, and stress index data at configurable frequencies.
    """
    
    def __init__(self, host="localhost", port=8765, stream_frequency=0.167, connector: Optional[SensorConnector] = None):
        """
        Initialize the biofeedback server.
        
        Args:
            host: Server host address
            port: Server port number
            stream_frequency: Streaming frequency in Hz (default: 0.167Hz for testing)
            connector: Sensor connector instance (defaults to SimConnector)
        """
        self.host = host
        self.port = port
        self.stream_frequency = stream_frequency
        self.stream_interval = 1.0 / stream_frequency
        
        # Initialize sensor connector
        self.connector = connector if connector is not None else SimConnector()
        
        # Connected clients tracking
        self.subscribers: Set = set()
        self.client_counter = 0
        
        # Session tracking
        self.session_data = []
        
        # Initialize sensor simulation
        self.running = False
        self.start_time = None
        
        logger.info(f"BiofeedbackServer initialized on {host}:{port}")
        logger.info(f"Streaming frequency: {stream_frequency}Hz (interval: {self.stream_interval:.3f}s)")
        logger.info(f"Sensor connector: {self.connector.__class__.__name__}")
    
    def generate_biofeedback_sample(self) -> Dict:
        """
        Generate a single biofeedback sample with timestamp.
        Integrates baseline protocol for resting period and baseline computation.
        
        Returns:
            Dictionary containing HR, EDA, stress, and metadata
        """
        # Get current sensor values from connector
        sensor_values = self.connector.read()
        hr = sensor_values["hr"]
        eda = sensor_values["eda"]
        hrv = sensor_values["hrv"]
        
        # Handle baseline protocol logic
        baseline_status = get_baseline_status()
        
        # Collect baseline sample if in baseline window
        if should_collect_baseline_sample():
            collect_baseline_sample(hr, eda, hrv)
            logger.info(f"Baseline sample collected: {len(baseline_status['baseline_samples_collected']) + 1}/{baseline_status['baseline_window_seconds']} samples")
            
            # Try to compute baseline values if we have enough samples
            if baseline_status['baseline_samples_collected'] >= 10:
                if compute_baseline_values():
                    logger.info("Baseline values computed successfully")
                    baseline_status = get_baseline_status()  # Refresh status
        
        # Calculate stress index with HRV integration
        stress = compute_stress_index(hr, eda, hrv)
        
        # Create MVP-compliant sample dict (exact format as specified)
        timestamp = datetime.now(timezone.utc).isoformat()
        sample = {
            "timestamp": timestamp,
            "hr": round(hr, 1),
            "eda": round(eda, 3),
            "hrv": round(hrv, 1),
            "stress": round(stress, 1),
            "scenario": get_current_scenario()
        }
        
        # Advance simulation time by stream interval for proper synchronization
        _advance_time(self.stream_interval)
        
        # Store for session logging
        self.session_data.append(sample)
        
        return sample
    
    async def handle_client_message(self, websocket, message: str) -> Optional[str]:
        """
        Process incoming client messages and return appropriate responses.
        
        Args:
            websocket: Client WebSocket connection
            message: JSON message from client
            
        Returns:
            JSON response string or None
        """
        try:
            request = json.loads(message)
            command = request.get("command", "").lower()
            
            if command == "once":
                # Single sample request
                sample = self.generate_biofeedback_sample()
                response = {
                    "type": "sample",
                    "data": sample
                }
                return json.dumps(response)
                
            elif command == "subscribe":
                # Add client to subscribers for continuous streaming
                self.subscribers.add(websocket)
                self.client_counter += 1
                
                logger.info(f"Client subscribed for streaming (total: {len(self.subscribers)})")
                
                response = {
                    "type": "subscription_confirmed",
                    "client_id": self.client_counter,
                    "stream_frequency_hz": self.stream_frequency,
                    "message": "Subscribed to continuous biofeedback stream"
                }
                return json.dumps(response)
                
            elif command == "unsubscribe":
                # Remove client from subscribers
                self.subscribers.discard(websocket)
                
                logger.info(f"Client unsubscribed (remaining: {len(self.subscribers)})")
                
                response = {
                    "type": "unsubscription_confirmed", 
                    "message": "Unsubscribed from biofeedback stream"
                }
                return json.dumps(response)
                
            elif command == "status":
                # Server status request
                uptime = time.time() - self.start_time if self.start_time else 0
                
                response = {
                    "type": "status",
                    "server": {
                        "running": self.running,
                        "uptime_seconds": round(uptime, 1),
                        "connected_clients": len(self.subscribers),
                        "stream_frequency_hz": self.stream_frequency,
                        "samples_generated": len(self.session_data)
                    }
                }
                return json.dumps(response)
                
            elif command == "set_frequency":
                # Change streaming frequency
                try:
                    hz = float(request.get("hz", self.stream_frequency))
                    
                    # Validate frequency range (0.1 Hz to 50 Hz)
                    if hz < 0.1 or hz > 50.0:
                        response = {
                            "type": "error",
                            "message": f"Invalid frequency: {hz}Hz. Must be between 0.1 and 50.0 Hz",
                            "current_frequency_hz": self.stream_frequency
                        }
                        return json.dumps(response)
                    
                    # Update frequency
                    old_frequency = self.stream_frequency
                    self.stream_frequency = hz
                    self.stream_interval = 1.0 / hz
                    
                    logger.info(f"Streaming frequency changed from {old_frequency}Hz to {hz}Hz")
                    
                    response = {
                        "type": "frequency_changed",
                        "old_frequency_hz": old_frequency,
                        "new_frequency_hz": self.stream_frequency,
                        "stream_interval_seconds": self.stream_interval,
                        "message": f"Streaming frequency changed to {hz}Hz"
                    }
                    return json.dumps(response)
                    
                except (ValueError, TypeError) as e:
                    response = {
                        "type": "error",
                        "message": f"Invalid frequency value: {request.get('hz', 'missing')}. Must be a number.",
                        "current_frequency_hz": self.stream_frequency
                    }
                    return json.dumps(response)
                    
            elif command == "set_scenario":
                # Change simulation scenario
                scenario = request.get("scenario", "")
                
                if scenario in ["baseline", "stress_buildup", "recovery", "mixed"]:
                    try:
                        set_scenario(scenario)
                        logger.info(f"Scenario changed to: {scenario}")
                        
                        response = {
                            "type": "scenario_changed",
                            "current_scenario": scenario,
                            "message": f"Simulation scenario changed to {scenario}"
                        }
                        return json.dumps(response)
                        
                    except Exception as e:
                        logger.error(f"Error setting scenario: {e}")
                        response = {
                            "type": "error",
                            "message": f"Failed to set scenario: {str(e)}"
                        }
                        return json.dumps(response)
                else:
                    response = {
                        "type": "error",
                        "message": f"Invalid scenario: {scenario}",
                        "valid_scenarios": ["baseline", "stress_buildup", "recovery", "mixed"]
                    }
                    return json.dumps(response)
                
            else:
                # Unknown command
                response = {
                    "type": "error",
                    "message": f"Unknown command: {command}",
                    "available_commands": ["once", "subscribe", "unsubscribe", "status", "set_frequency", "set_scenario"]
                }
                return json.dumps(response)
                
        except json.JSONDecodeError:
            response = {
                "type": "error",
                "message": "Invalid JSON format"
            }
            return json.dumps(response)
            
        except Exception as e:
            logger.error(f"Error handling client message: {e}")
            response = {
                "type": "error", 
                "message": f"Server error: {str(e)}"
            }
            return json.dumps(response)
    
    async def handle_client(self, websocket):
        """
        Handle individual client connections.
        
        Args:
            websocket: Client WebSocket connection
        """
        client_addr = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f"Client connected: {client_addr}")
        
        try:
            async for message in websocket:
                # Process client message
                response = await self.handle_client_message(websocket, message)
                
                if response:
                    await websocket.send(response)
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {client_addr}")
            
        except Exception as e:
            logger.error(f"Error with client {client_addr}: {e}")
            
        finally:
            # Clean up: remove from subscribers if present
            self.subscribers.discard(websocket)
    
    async def broadcast_to_subscribers(self):
        """
        Continuous loop to broadcast biofeedback data to all subscribers.
        """
        logger.info(f"Starting biofeedback broadcast loop at {self.stream_frequency}Hz")
        
        while self.running:
            if self.subscribers:
                # Generate new sample
                sample = self.generate_biofeedback_sample()
                
                # Create broadcast message with server info
                broadcast_data = {
                    "type": "stream",
                    "data": {
                        **sample,
                        "server_info": {
                            "frequency_hz": self.stream_frequency,
                            "connected_clients": len(self.subscribers)
                        }
                    }
                }
                message = json.dumps(broadcast_data)
                
                # Send to all subscribers (with error handling)
                disconnected_clients = set()
                
                for websocket in self.subscribers.copy():
                    try:
                        await websocket.send(message)
                    except websockets.exceptions.ConnectionClosed:
                        disconnected_clients.add(websocket)
                    except Exception as e:
                        logger.warning(f"Error sending to client: {e}")
                        disconnected_clients.add(websocket)
                
                # Remove disconnected clients
                for websocket in disconnected_clients:
                    self.subscribers.discard(websocket)
                    
                if disconnected_clients:
                    logger.info(f"Removed {len(disconnected_clients)} disconnected clients")
            
            # Wait for next broadcast interval
            await asyncio.sleep(self.stream_interval)
    
    async def start_server(self):
        """
        Start WebSocket server for biofeedback streaming (MVP-compliant).
        """
        logger.info(f"Starting biofeedback server on ws://{self.host}:{self.port}")
        
        self.running = True
        self.start_time = time.time()
        
        # Start WebSocket server (WebSocket-only as per MVP requirement)
        websocket_server = await websockets.serve(
            self.handle_client,
            self.host,
            self.port,
            ping_interval=20,  # Keep connections alive
            ping_timeout=10
        )
        
        logger.info(f"WebSocket server listening on ws://{self.host}:{self.port}")
        logger.info("Available WebSocket commands:")
        logger.info("  - Send '{\"command\": \"once\"}' for single sample")
        logger.info("  - Send '{\"command\": \"subscribe\"}' for continuous stream")
        logger.info("  - Send '{\"command\": \"status\"}' for server status")
        logger.info("  - Send '{\"command\": \"set_frequency\", \"hz\": <number>}' to change streaming rate")
        logger.info("  - Send '{\"command\": \"set_scenario\", \"scenario\": \"<mode>\"}' to switch scenarios")
        
        # Start broadcast loop
        broadcast_task = asyncio.create_task(self.broadcast_to_subscribers())
        
        try:
            # Keep servers running
            await websocket_server.wait_closed()
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            broadcast_task.cancel()
            await self.stop_server()
    
    async def stop_server(self):
        """
        Gracefully stop the server and save session data.
        """
        logger.info("Stopping biofeedback server...")
        
        self.running = False
        
        # Notify remaining clients
        if self.subscribers:
            shutdown_message = json.dumps({
                "type": "server_shutdown",
                "message": "Server is shutting down"
            })
            
            for websocket in self.subscribers.copy():
                try:
                    await websocket.send(shutdown_message)
                    await websocket.close()
                except:
                    pass
        
        # Save session data
        if self.session_data:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"../output/biofeedback_session_{timestamp}.json"
            
            try:
                with open(filename, 'w') as f:
                    session_log = {
                        "session_info": {
                            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
                            "duration_seconds": time.time() - self.start_time,
                            "samples_generated": len(self.session_data),
                            "stream_frequency_hz": self.stream_frequency
                        },
                        "data": self.session_data
                    }
                    json.dump(session_log, f, indent=2)
                
                logger.info(f"Session data saved to: {filename}")
                
            except Exception as e:
                logger.error(f"Failed to save session data: {e}")
        
        # Close sensor connector
        try:
            self.connector.close()
            logger.info("Sensor connector closed")
        except Exception as e:
            logger.error(f"Error closing sensor connector: {e}")
        
        logger.info("Server stopped gracefully")

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    sys.exit(0)

async def main():
    """Main function to run the biofeedback server."""
    print("="*60)
    print("Phase 3: Biofeedback WebSocket Server")
    print("="*60)
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start server
    server = BiofeedbackServer(
        host="localhost",
        port=8765,
        stream_frequency=0.167  # 0.167Hz streaming for ultra easy Unity verification (every 6 seconds)
    )
    
    try:
        await server.start_server()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Server startup failed: {e}")
        return 1
    finally:
        await server.stop_server()
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Server stopped by user")
        sys.exit(0)
