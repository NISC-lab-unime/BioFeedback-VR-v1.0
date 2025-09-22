#!/usr/bin/env python3
"""
Test client for biofeedback server - Phase 2 validation
"""
import asyncio
import json
import websockets

async def test_server():
    uri = "ws://localhost:8765"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("[OK] Connected to server")
            
            # Test 1: Get server status
            await websocket.send('{"command": "status"}')
            response = await websocket.recv()
            status_data = json.loads(response)
            print(f"[STATUS] Server: {status_data['server']['stream_frequency_hz']}Hz, {status_data['server']['connected_clients']} clients")
            
            # Test 2: Subscribe to stream
            await websocket.send('{"command": "subscribe"}')
            response = await websocket.recv()
            sub_data = json.loads(response)
            print(f"[SUBSCRIBE] {sub_data['message']}")
            
            # Test 3: Receive a few stream messages to check server_info
            print("[STREAM] Receiving stream messages...")
            for i in range(3):
                response = await websocket.recv()
                stream_data = json.loads(response)
                if stream_data['type'] == 'stream':
                    data = stream_data['data']
                    server_info = data.get('server_info', {})
                    print(f"[DATA] Sample {i+1}: HR={data['hr']:.1f}, EDA={data['eda']:.3f}, Stress={data['stress']:.1f}")
                    print(f"       Server Info: {server_info.get('frequency_hz', 'N/A')}Hz, {server_info.get('connected_clients', 'N/A')} clients")
            
            # Test 4: Change frequency
            print("[FREQ] Testing set_frequency command...")
            await websocket.send('{"command": "set_frequency", "hz": 1.0}')
            response = await websocket.recv()
            freq_data = json.loads(response)
            print(f"[FREQ] Response: {freq_data}")
            
            # Test 5: Verify new frequency in status
            await websocket.send('{"command": "status"}')
            response = await websocket.recv()
            new_status = json.loads(response)
            print(f"[VERIFY] New frequency confirmed: {new_status['server']['stream_frequency_hz']}Hz")
            
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_server())
