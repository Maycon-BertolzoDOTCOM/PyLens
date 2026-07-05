package formatter

import (
	"encoding/json"
	"fmt"
	"strings"

	"github.com/Maycon-BertolzoDOTCOM/PyLens/cmd/pylens/analyzer"
)

// Review holds the complete review output
type Review struct {
	Results    []analyzer.Result `json:"results"`
	OverallRegime string          `json:"overall_regime"`
	Summary    string             `json:"summary"`
	PR         *PRInfo            `json:"pr,omitempty"`
}

// PRInfo holds PR metadata
type PRInfo struct {
	Number int    `json:"number"`
	Title  string `json:"title"`
	Author string `json:"author"`
}

// NewReview creates a new Review from results
func NewReview(results []analyzer.Result, prInfo *PRInfo) *Review {
	overall := analyzer.GetOverallRegime(results)
	summary := generateSummary(results, overall)

	return &Review{
		Results:       results,
		OverallRegime: overall,
		Summary:       summary,
		PR:            prInfo,
	}
}

// Markdown formats the review as a GitHub PR comment
func (r *Review) Markdown() string {
	var sb strings.Builder

	sb.WriteString("## 🏗️ PyLens Architectural Review\n\n")

	// Summary
	sb.WriteString("### Overview\n\n")
	sb.WriteString(fmt.Sprintf("**Overall Regime:** `%s`\n\n", r.OverallRegime))
	sb.WriteString(r.Summary)
	sb.WriteString("\n\n")

	// Regime badge
	sb.WriteString(getRegimeBadge(r.OverallRegime))
	sb.WriteString("\n\n")

	// File-by-file analysis
	if len(r.Results) > 0 {
		sb.WriteString("### File Analysis\n\n")
		sb.WriteString("| File | Regime | Coupling | Cohesion | Decision | Risk |\n")
		sb.WriteString("|------|--------|----------|----------|----------|------|\n")

		for _, result := range r.Results {
			decision := result.Decision
			risk := result.Risk
			if result.RegimeWorsened {
				decision = "⚠️ " + decision
				risk = "HIGH"
			}
			sb.WriteString(fmt.Sprintf("| `%s` | `%s` | %.2f | %.2f | %s | %s |\n",
				result.FilePath,
				result.Regime,
				result.CouplingIndex,
				result.CohesionIndex,
				decision,
				risk,
			))
		}
		sb.WriteString("\n")
	}

	// Suggestions
	hasSuggestions := false
	for _, result := range r.Results {
		if len(result.Suggestions) > 0 {
			if !hasSuggestions {
				sb.WriteString("### 💡 Suggestions\n\n")
				hasSuggestions = true
			}
			sb.WriteString(fmt.Sprintf("**%s:**\n", result.FilePath))
			for _, s := range result.Suggestions {
				sb.WriteString(fmt.Sprintf("- [%s] %s\n", strings.ToUpper(s.Priority), s.Description))
				if s.CodeSnippet != "" {
					sb.WriteString(fmt.Sprintf("  ```python\n  %s\n  ```\n", s.CodeSnippet))
				}
			}
			sb.WriteString("\n")
		}
	}

	// Footer
	sb.WriteString("---\n")
	sb.WriteString("*Powered by [PyLens](https://github.com/Maycon-BertolzoDOTCOM/PyLens) — Architectural analysis for Python projects*\n")

	return sb.String()
}

// JSON formats the review as JSON
func (r *Review) JSON() string {
	data, _ := json.MarshalIndent(r, "", "  ")
	return string(data)
}

// generateSummary creates a human-readable summary
func generateSummary(results []analyzer.Result, overall string) string {
	total := len(results)
	coupled := 0
	entangled := 0
	perfect := 0

	for _, r := range results {
		switch {
		case strings.Contains(r.Regime, "COUPLED"):
			coupled++
		case strings.Contains(r.Regime, "ENTANGLED"):
			entangled++
		case r.Regime == "PERFECT":
			perfect++
		}
	}

	var sb strings.Builder

	if total == 0 {
		sb.WriteString("No Python files analyzed.")
		return sb.String()
	}

	if perfect > 0 {
		sb.WriteString(fmt.Sprintf("**%d** file(s) with perfect structure. ", perfect))
	}
	if coupled > 0 {
		sb.WriteString(fmt.Sprintf("**%d** file(s) with coupling issues. ", coupled))
	}
	if entangled > 0 {
		sb.WriteString(fmt.Sprintf("**%d** file(s) severely entangled. ", entangled))
	}

	switch overall {
	case "PERFECT":
		sb.WriteString("The code is well-structured and maintainable.")
	case "MODULAR_SMALL", "MODULAR_LARGE":
		sb.WriteString("The code follows good modular practices.")
	case "COUPLED":
		sb.WriteString("Consider refactoring to reduce coupling between modules.")
	case "ENTANGLED_SMALL", "ENTANGLED_LARGE":
		sb.WriteString("⚠️ The code is heavily entangled. Refactoring is recommended.")
	case "LEAKY":
		sb.WriteString("Abstraction boundaries are being violated.")
	case "COLLAPSED":
		sb.WriteString("🚨 The architecture has collapsed. Major refactoring needed.")
	case "MIXED":
		sb.WriteString("Mixed architectural patterns detected.")
	default:
		sb.WriteString("Analysis complete.")
	}

	return sb.String()
}

// getRegimeBadge returns an emoji badge for the regime
func getRegimeBadge(regime string) string {
	badges := map[string]string{
		"PERFECT":          "🟢 **PERFECT**",
		"MODULAR_SMALL":    "🟢 **MODULAR**",
		"MODULAR_LARGE":    "🟢 **MODULAR**",
		"COUPLED":          "🟡 **COUPLED**",
		"ENTANGLED_SMALL":  "🟠 **ENTANGLED**",
		"ENTANGLED_LARGE":  "🔴 **ENTANGLED**",
		"LEAKY":            "🟠 **LEAKY**",
		"COLLAPSED":        "🔴 **COLLAPSED**",
		"MIXED":            "🟡 **MIXED**",
		"PATHOLOGICAL":     "🔴 **PATHOLOGICAL**",
		"ACYCLIC_DOMINANT": "🟢 **ACYCLIC**",
	}

	if badge, ok := badges[regime]; ok {
		return badge
	}
	return fmt.Sprintf("⚪ **%s**", regime)
}
