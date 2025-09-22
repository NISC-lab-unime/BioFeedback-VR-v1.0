using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine.SceneManagement;
using TMPro;
using UnityEngine.UI;

public class SceneSetup : MonoBehaviour {
    [MenuItem("Biofeedback/Setup Scene")]
    public static void SetupBiofeedbackScene() {
        // Create new scene
        Scene newScene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        newScene.name = "ControlScene";
        
        // Create Main Camera (ESSENTIAL!)
        GameObject cameraGO = new GameObject("Main Camera");
        Camera camera = cameraGO.AddComponent<Camera>();
        camera.backgroundColor = Color.black;
        camera.clearFlags = CameraClearFlags.SolidColor;
        cameraGO.tag = "MainCamera";
        cameraGO.transform.position = new Vector3(0, 1, -10);
        
        // Add AudioListener to camera
        cameraGO.AddComponent<AudioListener>();
        
        // Create Canvas
        GameObject canvasGO = new GameObject("Canvas");
        Canvas canvas = canvasGO.AddComponent<Canvas>();
        canvas.renderMode = RenderMode.ScreenSpaceOverlay;
        canvas.sortingOrder = 100;  // Ensure UI is on top
        
        CanvasScaler scaler = canvasGO.AddComponent<CanvasScaler>();
        scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
        scaler.referenceResolution = new Vector2(1920, 1080);
        
        canvasGO.AddComponent<GraphicRaycaster>();
        
        // Create UI Panel in top-right corner
        GameObject panelGO = new GameObject("BiofeedbackPanel");
        panelGO.transform.SetParent(canvasGO.transform, false);
        
        RectTransform panelRect = panelGO.AddComponent<RectTransform>();
        panelRect.anchorMin = new Vector2(1, 1);  // Top-right
        panelRect.anchorMax = new Vector2(1, 1);  // Top-right
        panelRect.anchoredPosition = new Vector2(-120, -80);  // Offset from corner
        panelRect.sizeDelta = new Vector2(220, 120);
        
        // Add background to panel
        Image panelBG = panelGO.AddComponent<Image>();
        panelBG.color = new Color(0, 0, 0, 0.7f);  // Semi-transparent black
        
        // Create HR Text
        GameObject hrTextGO = CreateTextElement("HRText", "HR: Connecting...", panelGO.transform);
        RectTransform hrRect = hrTextGO.GetComponent<RectTransform>();
        hrRect.anchoredPosition = new Vector2(0, 30);
        
        // Create EDA Text  
        GameObject edaTextGO = CreateTextElement("EDAText", "EDA: Connecting...", panelGO.transform);
        RectTransform edaRect = edaTextGO.GetComponent<RectTransform>();
        edaRect.anchoredPosition = new Vector2(0, 0);
        
        // Create Stress Text
        GameObject stressTextGO = CreateTextElement("StressText", "Stress: Connecting...", panelGO.transform);
        RectTransform stressRect = stressTextGO.GetComponent<RectTransform>();
        stressRect.anchoredPosition = new Vector2(0, -30);
        
        // Add WebSocket client to Canvas
        BioWebsocketClient client = canvasGO.AddComponent<BioWebsocketClient>();
        client.hrText = hrTextGO.GetComponent<TMP_Text>();
        client.edaText = edaTextGO.GetComponent<TMP_Text>();
        client.stressText = stressTextGO.GetComponent<TMP_Text>();
        
        // Create EventSystem for UI interaction
        GameObject eventSystemGO = new GameObject("EventSystem");
        eventSystemGO.AddComponent<UnityEngine.EventSystems.EventSystem>();
        eventSystemGO.AddComponent<UnityEngine.EventSystems.StandaloneInputModule>();
        
        // Ensure scenes folder exists
        if (!AssetDatabase.IsValidFolder("Assets/Scenes")) {
            AssetDatabase.CreateFolder("Assets", "Scenes");
        }
        
        // Save scene
        EditorSceneManager.SaveScene(newScene, "Assets/Scenes/ControlScene.unity");
        
        Debug.Log("[SceneSetup] Complete biofeedback scene created with Main Camera and UI dashboard!");
    }

    static GameObject CreateTextElement(string name, string text, Transform parent) {
        GameObject textGO = new GameObject(name);
        textGO.transform.SetParent(parent, false);
        
        TMP_Text textComponent = textGO.AddComponent<TMP_Text>();
        textComponent.text = text;
        textComponent.fontSize = 18;
        textComponent.color = Color.white;
        textComponent.alignment = TextAlignmentOptions.Center;
        textComponent.fontStyle = FontStyles.Bold;
        
        RectTransform textRect = textGO.GetComponent<RectTransform>();
        textRect.sizeDelta = new Vector2(200, 30);
        
        return textGO;
    }
}
