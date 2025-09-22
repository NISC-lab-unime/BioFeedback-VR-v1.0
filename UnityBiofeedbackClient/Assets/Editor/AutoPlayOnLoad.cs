using UnityEditor;

[InitializeOnLoad]
public static class AutoPlayOnLoad {
    static AutoPlayOnLoad() {
        // Auto-enter play mode when Unity loads (useful for testing)
        // Only activate if not already in play mode and scene is set up
        if (!EditorApplication.isPlaying && EditorPrefs.GetBool("BiofeedbackDemo_Scaffolded")) {
            UnityEngine.Debug.Log("[AutoPlay] Entering play mode for biofeedback demo");
            EditorApplication.EnterPlaymode();
        }
    }
}
