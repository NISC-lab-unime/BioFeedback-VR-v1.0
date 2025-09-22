using UnityEditor;
using System.Collections.Generic;
using UnityEngine;

public class BuildScript {
    [MenuItem("Build/Standalone")]
    public static void BuildStandalone() {
        // Ensure scene is included in build
        var scenes = new List<string> { "Assets/Scenes/ControlScene.unity" };
        
        var opts = new BuildPlayerOptions {
            scenes = scenes.ToArray(),
            locationPathName = "Builds/BiofeedbackDemo.exe",
            target = BuildTarget.StandaloneWindows64,
            options = BuildOptions.AutoRunPlayer | BuildOptions.Development
        };
        
        Debug.Log("[BuildScript] Building biofeedback demo standalone...");
        
        var result = BuildPipeline.BuildPlayer(opts);
        
        if (result.summary.result == UnityEditor.Build.Reporting.BuildResult.Succeeded) {
            Debug.Log($"[BuildScript] Build succeeded: {opts.locationPathName}");
            Debug.Log($"[BuildScript] Build size: {result.summary.totalSize} bytes");
        } else {
            Debug.LogError($"[BuildScript] Build failed: {result.summary.result}");
            foreach (var step in result.steps) {
                foreach (var message in step.messages) {
                    if (message.type == LogType.Error) {
                        Debug.LogError($"Build error: {message.content}");
                    }
                }
            }
        }
    }
    
    [MenuItem("Build/Standalone (Release)")]
    public static void BuildStandaloneRelease() {
        var scenes = new List<string> { "Assets/Scenes/ControlScene.unity" };
        
        var opts = new BuildPlayerOptions {
            scenes = scenes.ToArray(),
            locationPathName = "Builds/BiofeedbackDemo_Release.exe",
            target = BuildTarget.StandaloneWindows64,
            options = BuildOptions.AutoRunPlayer
        };
        
        Debug.Log("[BuildScript] Building release version...");
        BuildPipeline.BuildPlayer(opts);
    }
}
