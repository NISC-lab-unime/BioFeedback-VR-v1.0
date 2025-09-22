#!/usr/bin/env python3
"""
Unity Data Verification Script
=============================

This script connects to the same Python biofeedback server as Unity
and prints the REAL simulation values to the terminal.

Run this alongside Unity to verify that Unity is displaying
genuine simulation data from sensors.py and NOT fake data.

Usage:
    python temp/verify_unity_data.py

Expected: Terminal output should EXACTLY match Unity display
"""

import asyncio
import websockets
import json
import sys
import os
from datetime import datetime

# Add src directory to path to import sensors
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

async def verify_unity_data():
    """Connect to Python server and print real simulation values for Unity comparison."""
    
    server_url = "ws://localhost:8765"
    
    print("="*60)
    print("UNITY DATA VERIFICATION - REAL PYTHON SIMULATION VALUES")
    print("="*60)
    print(f"Connecting to Python server: {server_url}")
    print("Run Unity BiofeedbackDemo project now and compare values!")
    print("="*60)
    print()
    
    try:
        # Connect to the same Python server that Unity connects to
        async with websockets.connect(server_url) as websocket:
            print("✅ Connected to Python biofeedback server")
            print("📡 Sending subscription command...")
            
            # Send the exact same subscribe command that Unity sends
            subscribe_command = {"command": "subscribe"}
            await websocket.send(json.dumps(subscribe_command))
            
            print("🔄 Receiving REAL simulation data from sensors.py...")
            print()
            print("TIME     | HR      | EDA     | STRESS  | SCENARIO")
            print("-" * 55)
            
            sample_count = 0
            
            # Receive and display real simulation data
            async for message in websocket:
                try:
                    # Parse the exact same message format that Unity receives
                    data = json.loads(message)
                    
                    if data.get("type") == "stream" and "data" in data:
                        # Extract the real simulation values
                        sim_data = data["data"]
                        
                        hr = sim_data.get("hr", 0)
                        eda = sim_data.get("eda", 0) 
                        stress = sim_data.get("stress", 0)
                        scenario = sim_data.get("scenario", "unknown")
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        
                        # Print every sample at the same rate as the server
                        print(f"{timestamp} | {hr:6.1f} | {eda:6.3f} | {stress:6.1f} | {scenario}")
                        
                        sample_count += 1
                        
                        # Show periodic summary
                        if sample_count % 50 == 0:
                            print(f"\n📊 Received {sample_count} genuine simulation samples")
                            print("💡 Compare these values with Unity display - they should MATCH!")
                            print("-" * 55)
                            
                    elif data.get("type") == "subscription_confirmed":
                        print("✅ Python server confirmed subscription - starting data stream...")
                        print()
                        
                except json.JSONDecodeError:
                    print(f"❌ Failed to parse message: {message}")
                except Exception as e:
                    print(f"❌ Error processing data: {e}")
                    
    except ConnectionRefusedError:
        print("❌ ERROR: Cannot connect to Python server!")
        print("   Make sure biofeedback_server.py is running on ws://localhost:8765")
        print("   Run: python src/biofeedback_server.py")
        
    except Exception as e:
        print(f"❌ Connection error: {e}")

def main():
    """Run the Unity data verification."""
    print("Starting Unity data verification...")
    print("This will show the REAL simulation values that Unity should display")
    print()
    
    try:
        asyncio.run(verify_unity_data())
    except KeyboardInterrupt:
        print("\n🛑 Verification stopped by user")
        print("✅ If Unity values matched terminal output, Unity is using REAL data!")
        
if __name__ == "__main__":
    main()
