package cmd

import (
	"fmt"
	"os"

	"github.com/Maycon-BertolzoDOTCOM/PyLens/cmd/pylens/analyzer"
	"github.com/Maycon-BertolzoDOTCOM/PyLens/cmd/pylens/formatter"
	"github.com/Maycon-BertolzoDOTCOM/PyLens/cmd/pylens/github"
	"github.com/Maycon-BertolzoDOTCOM/PyLens/cmd/pylens/tui"
	"github.com/spf13/cobra"
)

var reviewCmd = &cobra.Command{
	Use:   "review",
	Short: "Review a PR and post architectural analysis as a comment",
	Long: `Fetches the PR diff, runs PyLens analysis, and posts
a formatted architectural review as a PR comment.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		prNum, _ := cmd.Flags().GetInt("pr")
		repo, _ := cmd.Flags().GetString("repo")
		tuiMode, _ := cmd.Flags().GetBool("tui")
		jsonOutput, _ := cmd.Flags().GetBool("json")

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

		fmt.Fprintf(os.Stderr, "Reviewing PR #%d in %s\n", prNum, repo)

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
			fmt.Fprintln(os.Stderr, "No Python files changed in this PR")
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

		if len(results) == 0 {
			fmt.Fprintln(os.Stderr, "No results from analysis")
			return nil
		}

		if tuiMode {
			// Run TUI mode
			return tui.RunReview(results, prData)
		}

		// Format review
		review := formatter.NewReview(results, &formatter.PRInfo{
			Number: prData.Number,
			Title:  prData.Title,
			Author: prData.Author,
		})

		if jsonOutput {
			fmt.Println(review.JSON())
			return nil
		}

		// Post comment to PR
		if err := client.PostComment(repo, prNum, review.Markdown()); err != nil {
			return fmt.Errorf("failed to post comment: %w", err)
		}

		fmt.Fprintf(os.Stderr, "✓ Review posted to PR #%d\n", prNum)
		return nil
	},
}

func init() {
	reviewCmd.Flags().IntP("pr", "p", 0, "PR number (auto-detected if not provided)")
	reviewCmd.Flags().StringP("repo", "r", "", "Repository in owner/repo format (auto-detected)")
	reviewCmd.Flags().Bool("tui", false, "Run in TUI mode")
	rootCmd.AddCommand(reviewCmd)
}
