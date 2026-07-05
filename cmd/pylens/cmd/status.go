package cmd

import (
	"fmt"

	"github.com/Maycon-BertolzoDOTCOM/PyLens/cmd/pylens/github"
	"github.com/spf13/cobra"
)

var statusCmd = &cobra.Command{
	Use:   "status",
	Short: "Show PyLens analysis status for a PR",
	Long: `Displays the architectural status of a PR based on
previous PyLens reviews or current diff analysis.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		prNum, _ := cmd.Flags().GetInt("pr")
		repo, _ := cmd.Flags().GetString("repo")

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

		client, err := github.NewClient()
		if err != nil {
			return fmt.Errorf("github client error: %w", err)
		}

		// Check for existing PyLens comment
		comment, err := client.FindExistingReview(repo, prNum)
		if err != nil {
			return fmt.Errorf("failed to search for reviews: %w", err)
		}

		if comment != nil {
			fmt.Printf("PyLens review found (posted %s)\n", comment.CreatedAt)
			fmt.Printf("Author: %s\n", comment.Author)
			fmt.Println("\n---")
			fmt.Println(comment.Body)
			return nil
		}

		// No existing review - offer to run one
		fmt.Println("No PyLens review found for this PR")
		fmt.Printf("Run 'pylens review --pr %d' to create one\n", prNum)
		return nil
	},
}

func init() {
	statusCmd.Flags().IntP("pr", "p", 0, "PR number (auto-detected if not provided)")
	statusCmd.Flags().StringP("repo", "r", "", "Repository in owner/repo format (auto-detected)")
	rootCmd.AddCommand(statusCmd)
}
