package cmd

import (
	"fmt"
	"os"

	"github.com/Maycon-BertolzoDOTCOM/PyLens/cmd/pylens/analyzer"
	"github.com/Maycon-BertolzoDOTCOM/PyLens/cmd/pylens/github"
	"github.com/spf13/cobra"
)

var checkCmd = &cobra.Command{
	Use:   "check",
	Short: "Check if PR changes improve or worsen architecture",
	Long: `Analyzes the PR diff and exits with code 1 if architectural
regression is detected. Useful for CI pipelines.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		prNum, _ := cmd.Flags().GetInt("pr")
		repo, _ := cmd.Flags().GetString("repo")
		strict, _ := cmd.Flags().GetBool("strict")

		// Resolve PR number
		if prNum == 0 {
			var err error
			prNum, err = github.GetCurrentPR()
			if err != nil {
				return fmt.Errorf("could not determine PR number: %w", err)
			}
		}

		// Resolve repo
		if repo == "" {
			var err error
			repo, err = github.GetCurrentRepo()
			if err != nil {
				return fmt.Errorf("could not determine repo: %w", err)
			}
		}

		fmt.Fprintf(os.Stderr, "Checking PR #%d in %s\n", prNum, repo)

		// Fetch PR data
		client, err := github.NewClient()
		if err != nil {
			return fmt.Errorf("github client error: %w", err)
		}

		prData, err := client.GetPR(repo, prNum)
		if err != nil {
			return fmt.Errorf("failed to fetch PR: %w", err)
		}

		// Parse Python files from diff
		pythonFiles := github.ParsePythonFiles(prData.Files)
		if len(pythonFiles) == 0 {
			fmt.Println("✓ No Python files changed")
			return nil
		}

		fmt.Fprintf(os.Stderr, "Analyzing %d Python files...\n", len(pythonFiles))

		// Analyze each file
		files := make(map[string]string)
		for _, file := range pythonFiles {
			files[file.Path] = file.Content
		}

		results, err := analyzer.AnalyzeMultiple(files)
		if err != nil {
			return fmt.Errorf("analysis failed: %w", err)
		}

		// Check for regressions
		hasRegression := false
		for _, r := range results {
			if r.Decision == "MANUAL_REFACTOR" || r.Decision == "SKIP" {
				if strict && r.Decision == "MANUAL_REFACTOR" {
					hasRegression = true
				}
			}
		if r.RegimeWorsened {
			hasRegression = true
			fmt.Fprintf(os.Stderr, "⚠ %s: regime worsened from %s to %s\n",
				r.FilePath, r.PreviousRegime, r.Regime)
		}
		}

		if hasRegression {
			fmt.Fprintln(os.Stderr, "✗ Architectural regression detected")
			os.Exit(1)
		}

		fmt.Fprintln(os.Stderr, "✓ No architectural regressions detected")
		return nil
	},
}

func init() {
	checkCmd.Flags().IntP("pr", "p", 0, "PR number (auto-detected if not provided)")
	checkCmd.Flags().StringP("repo", "r", "", "Repository in owner/repo format (auto-detected)")
	checkCmd.Flags().Bool("strict", false, "Fail on MANUAL_REFACTOR decisions")
	rootCmd.AddCommand(checkCmd)
}
