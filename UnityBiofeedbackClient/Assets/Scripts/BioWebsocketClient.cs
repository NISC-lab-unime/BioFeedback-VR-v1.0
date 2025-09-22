using UnityEngine;
using TMPro;
using System.Collections;
using System;
using System.Text;
using System.Net.WebSockets;
using System.Threading;
using System.Threading.Tasks;

public class BioWebsocketClient : MonoBehaviour {
    [Header("WebSocket Settings")]
    public string serverUrl = "ws://localhost:8765";
    
    [Header("Reconnect Settings")]
    public bool autoReconnect = true;
    public float initialBackoffSeconds = 1f;
    public float maxBackoffSeconds = 30f;
    
    [Header("UI References - Auto-assigned")]
    public TMP_Text hrText;
    public TMP_Text edaText; 
    public TMP_Text stressText;
    
    private ClientWebSocket webSocket;
    private CancellationTokenSource cancellationTokenSource;
    private bool isConnected = false;
    
    void Start() {
        // Auto-find UI components if not assigned
        if (hrText == null) hrText = GameObject.Find("HRText")?.GetComponent<TMP_Text>();
        if (edaText == null) edaText = GameObject.Find("EDAText")?.GetComponent<TMP_Text>();
        if (stressText == null) stressText = GameObject.Find("StressText")?.GetComponent<TMP_Text>();
        
        Debug.Log("[BioWebsocketClient] Starting connection manager");
        
        // Start connection manager with auto-reconnect
        StartCoroutine(ConnectionManagerLoop());
    }
    
    IEnumerator ConnectionManagerLoop() {
        float backoff = initialBackoffSeconds;
        
        while (true) {
            Debug.Log("[BioWebsocketClient] Starting connection attempt...");
            
            // Try to connect and run
            yield return StartCoroutine(ConnectAndRun());
            
            // Connection ended - show error state
            SetConnectionError();
            
            // Exit if auto-reconnect is disabled
            if (!autoReconnect) {
                Debug.Log("[BioWebsocketClient] Auto-reconnect disabled, stopping");
                yield break;
            }
            
            // Wait before retry with exponential backoff
            Debug.Log($"[BioWebsocketClient] Reconnecting in {backoff:F1}s...");
            yield return new WaitForSeconds(backoff);
            
            // Increase backoff for next attempt (exponential backoff)
            backoff = Mathf.Min(backoff * 2f, maxBackoffSeconds);
        }
    }
    
    IEnumerator ConnectAndRun() {
        // Create fresh socket and cancellation token for this attempt
        webSocket = new ClientWebSocket();
        webSocket.Options.KeepAliveInterval = TimeSpan.FromSeconds(10);
        cancellationTokenSource = new CancellationTokenSource();
        
        Uri serverUri = new Uri(serverUrl);
        
        // Connect with timeout
        var connectTask = Task.Run(async () => {
            try {
                await webSocket.ConnectAsync(serverUri, cancellationTokenSource.Token);
                return true;
            } catch (Exception e) {
                Debug.LogWarning($"[BioWebsocketClient] Connection failed: {e.Message}");
                return false;
            }
        });
        
        float timeout = 5f, elapsed = 0f;
        while (!connectTask.IsCompleted && elapsed < timeout) {
            elapsed += Time.deltaTime;
            yield return null;
        }
        
        if (!connectTask.IsCompleted || !connectTask.Result || webSocket.State != WebSocketState.Open) {
            // Connection failed
            yield break;
        }
        
        Debug.Log("[BioWebsocketClient] Connected successfully!");
        isConnected = true;
        
        // Send subscribe command
        SendSubscribeCommand();
        
        // Run receive loop (returns when connection ends)
        yield return ReceiveRealDataFromPython();
        
        // Cleanup
        isConnected = false;
        try {
            if (webSocket.State == WebSocketState.Open) {
                webSocket.CloseAsync(WebSocketCloseStatus.NormalClosure, "closing", CancellationToken.None);
            }
        } catch { }
        
        cancellationTokenSource?.Cancel();
        webSocket?.Dispose();
        cancellationTokenSource?.Dispose();
    }
    
    void SendSubscribeCommand() {
        try {
            // Send exact command that Python server expects
            string subscribeMessage = "{\"command\": \"subscribe\"}";
            byte[] messageBytes = Encoding.UTF8.GetBytes(subscribeMessage);
            
            Debug.Log($"[BioWebsocketClient] Sending subscribe to Python: {subscribeMessage}");
            
            var sendTask = webSocket.SendAsync(
                new ArraySegment<byte>(messageBytes),
                WebSocketMessageType.Text,
                true,
                cancellationTokenSource.Token
            );
        } catch (Exception e) {
            Debug.LogError($"[BioWebsocketClient] Failed to send subscribe: {e.Message}");
        }
    }
    
    IEnumerator ReceiveRealDataFromPython() {
        byte[] buffer = new byte[4096];
        
        while (isConnected && webSocket.State == WebSocketState.Open) {
            var receiveTask = Task.Run(async () => {
                try {
                    return await webSocket.ReceiveAsync(
                        new ArraySegment<byte>(buffer),
                        cancellationTokenSource.Token
                    );
                } catch (Exception e) {
                    Debug.LogError($"[BioWebsocketClient] Receive error: {e.Message}");
                    return null;
                }
            });
            
            // Wait for Python server response
            while (!receiveTask.IsCompleted) {
                yield return null;
            }
            
            if (receiveTask.IsCompleted && receiveTask.Result != null) {
                WebSocketReceiveResult result = receiveTask.Result;
                
                if (result.MessageType == WebSocketMessageType.Text) {
                    string message = Encoding.UTF8.GetString(buffer, 0, result.Count);
                    Debug.Log($"[BioWebsocketClient] Received from Python: {message}");
                    ProcessRealPythonData(message);
                } else if (result.MessageType == WebSocketMessageType.Close) {
                    Debug.Log("[BioWebsocketClient] Python server closed connection");
                    break;
                }
            } else {
                Debug.LogError("[BioWebsocketClient] Failed to receive from Python server");
                break;
            }
        }
        
        isConnected = false;
        SetConnectionError();
    }
    
    void ProcessRealPythonData(string message) {
        try {
            // Parse real data from Python server - exact protocol match
            var pythonResponse = JsonUtility.FromJson<BiofeedbackResponse>(message);
            
            Debug.Log($"[BioWebsocketClient] Python message type: {pythonResponse?.type}");
            
            if (pythonResponse?.type == "stream" && pythonResponse.data != null) {
                Debug.Log($"[BioWebsocketClient] Real Python data - HR: {pythonResponse.data.hr}, EDA: {pythonResponse.data.eda}, Stress: {pythonResponse.data.stress}");
                
                // Update UI with ONLY real simulation data from Python sensors.py
                UpdateBiofeedbackDisplay(pythonResponse.data);
            } else if (pythonResponse?.type == "subscription_confirmed") {
                Debug.Log("[BioWebsocketClient] Python server confirmed subscription");
            } else {
                Debug.Log($"[BioWebsocketClient] Unknown Python message: {pythonResponse?.type}");
            }
        } catch (Exception e) {
            Debug.LogError($"[BioWebsocketClient] Failed to parse Python data: {e.Message}");
            Debug.LogError($"[BioWebsocketClient] Raw message: {message}");
        }
    }
    

    
    void UpdateBiofeedbackDisplay(BiofeedbackData data) {
        // Display ONLY real simulation data from Python sensors.py
        if (hrText != null) hrText.text = $"HR: {data.hr:F1} bpm";
        if (edaText != null) edaText.text = $"EDA: {data.eda:F3} µS";  // Match Python 3 decimal places
        if (stressText != null) stressText.text = $"Stress: {data.stress:F1}";  // Match Python 1 decimal place
    }
    
    void SetConnectionError() {
        if (hrText != null) hrText.text = "HR: Server Offline";
        if (edaText != null) edaText.text = "EDA: Server Offline";
        if (stressText != null) stressText.text = "Stress: Server Offline";
    }
    
    void SetErrorState(string error) {
        if (hrText != null) hrText.text = $"HR: {error}";
        if (edaText != null) edaText.text = $"EDA: {error}";
        if (stressText != null) stressText.text = $"Stress: {error}";
    }
    
    public void RetryConnection() {
        // Manual retry - restart connection manager
        StopAllCoroutines();
        StartCoroutine(ConnectionManagerLoop());
    }
    
    void OnDestroy() {
        isConnected = false;
        autoReconnect = false; // Stop auto-reconnect when destroying
        
        // Clean up WebSocket connection
        if (webSocket != null && webSocket.State == WebSocketState.Open) {
            webSocket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Unity client closing", CancellationToken.None);
        }
        
        cancellationTokenSource?.Cancel();
        webSocket?.Dispose();
        cancellationTokenSource?.Dispose();
    }
}

[System.Serializable]
public class BiofeedbackResponse {
    public string type;
    public string message;
    public BiofeedbackData data;
}

[System.Serializable]
public class BiofeedbackData {
    public string timestamp;
    public float session_time;
    public float hr;
    public float eda;
    public float stress;
    public string scenario;
    public ServerInfo server_info;
}

[System.Serializable]
public class ServerInfo {
    public int frequency_hz;
    public int connected_clients;
}
