package analyzer

import (
	"encoding/json"
	"fmt"
	"os/exec"
	"path/filepath"
	"strings"
)

// Result holds analysis output for a single file
type Result struct {
	FilePath       string            `json:"file_path"`
	Classes        []ClassAnalysis   `json:"classes"`
	Functions      []FuncAnalysis    `json:"functions"`
	Imports        []string          `json:"imports"`
	PyArch         PyArchMetrics     `json:"pyarch"`
	CouplingIndex  float64           `json:"coupling_index"`
	CohesionIndex  float64           `json:"cohesion_index"`
	LeakageRatio   float64           `json:"leakage_ratio"`
	CyclicRatio    float64           `json:"cyclic_ratio"`
	Regime         string            `json:"regime"`
	PreviousRegime string            `json:"previous_regime,omitempty"`
	RegimeWorsened bool              `json:"regime_worsened"`
	Decision       string            `json:"decision"`
	Risk           string            `json:"risk"`
	Confidence     float64           `json:"confidence"`
	Suggestions    []Suggestion      `json:"suggestions"`
}

// ClassAnalysis holds class-level metrics
type ClassAnalysis struct {
	Name              string   `json:"name"`
	Methods           []string `json:"methods"`
	AfferentCoupling  int      `json:"afferent_coupling"`
	EfferentCoupling  int      `json:"efferent_coupling"`
	Instability       float64  `json:"instability"`
	Abstractness      float64  `json:"abstractness"`
}

// FuncAnalysis holds function-level metrics
type FuncAnalysis struct {
	Name       string `json:"name"`
	Params     int    `json:"params"`
	Loc        int    `json:"loc"`
	Complexity int    `json:"cyclomatic_complexity"`
}

// PyArchMetrics holds PyArch (formerly FASM) metrics
type PyArchMetrics struct {
	Coupling      float64 `json:"coupling"`
	Cohesion      float64 `json:"cohesion"`
	Complexity    float64 `json:"complexity"`
	Modularity    float64 `json:"modularity"`
	Encapsulation float64 `json:"encapsulation"`
}

// Suggestion holds a refactoring suggestion
type Suggestion struct {
	Type        string `json:"type"`
	Priority    string `json:"priority"`
	Description string `json:"description"`
	CodeSnippet string `json:"code_snippet,omitempty"`
}

// AnalyzeFile runs PyLens analysis on a Python file
func AnalyzeFile(filePath string, content string) (*Result, error) {
	// Create temp file with content
	tmpFile, err := filepath.Abs(filePath)
	if err != nil {
		return nil, fmt.Errorf("invalid path: %w", err)
	}

	// Call PyLens Python API
	cmd := exec.Command("python", "-m", "pylens", "analyze", "--file", tmpFile, "--json")
	output, err := cmd.CombinedOutput()
	if err != nil {
		// Try alternative: direct Python script
		return analyzeWithPython(filePath, content)
	}

	var result Result
	if err := json.Unmarshal(output, &result); err != nil {
		return nil, fmt.Errorf("failed to parse analysis output: %w", err)
	}

	return &result, nil
}

// analyzeWithPython is a fallback that runs analysis via Python
func analyzeWithPython(filePath string, content string) (*Result, error) {
	// Create a Python script that imports PyLens and analyzes
	pythonScript := fmt.Sprintf(`
import sys
import json
sys.path.insert(0, '/home/vector/Documentos/Crystalize/pylens')

from app.analysis.static_analysis import analyze_file
from app.analysis.architectural import classify_architecture

content = """%s"""
filepath = "%s"

# Run static analysis
metrics = analyze_file(filepath, content)

# Classify architecture
regime, confidence = classify_architecture(metrics)

# Get decision
from app.decision_engine import decide
decision = decide(metrics)

result = {
    "file_path": filepath,
    "pyarch": {
        "coupling": metrics.get("coupling_index", 0),
        "cohesion": metrics.get("cohesion_index", 0),
        "complexity": metrics.get("complexity", 0),
        "modularity": metrics.get("modularity", 0),
        "encapsulation": metrics.get("encapsulation", 0)
    },
    "coupling_index": metrics.get("coupling_index", 0),
    "cohesion_index": metrics.get("cohesion_index", 0),
    "leakage_ratio": metrics.get("leakage_ratio", 0),
    "cyclic_ratio": metrics.get("cyclic_ratio", 0),
    "regime": regime,
    "decision": decision.get("action", "ANALYZE"),
    "risk": decision.get("risk", "low"),
    "confidence": confidence,
    "suggestions": decision.get("suggestions", [])
}

print(json.dumps(result))
`, strings.ReplaceAll(content, "`", "\\`"), filePath)

	cmd := exec.Command("python", "-c", pythonScript)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return nil, fmt.Errorf("python analysis failed: %s: %w", string(output), err)
	}

	var result Result
	if err := json.Unmarshal(output, &result); err != nil {
		return nil, fmt.Errorf("failed to parse python output: %w", err)
	}

	return &result, nil
}

// AnalyzeMultiple analyzes multiple files and returns aggregate results
func AnalyzeMultiple(files map[string]string) ([]Result, error) {
	var results []Result
	for path, content := range files {
		result, err := AnalyzeFile(path, content)
		if err != nil {
			continue
		}
		results = append(results, *result)
	}
	return results, nil
}

// GetOverallRegime determines the overall regime from individual file results
func GetOverallRegime(results []Result) string {
	regimeCounts := make(map[string]int)
	for _, r := range results {
		regimeCounts[r.Regime]++
	}

	// Find most common regime
	maxCount := 0
	mostCommon := "UNKNOWN"
	for regime, count := range regimeCounts {
		if count > maxCount {
			maxCount = count
			mostCommon = regime
		}
	}

	return mostCommon
}
