package cmd

import (
	"github.com/spf13/cobra"
)

var rootCmd = &cobra.Command{
	Use:   "pylens",
	Short: "PyLens - Architectural analysis for Python projects",
	Long: `PyLens is a GitHub-integrated tool that analyzes Python code
architecture and provides actionable insights for refactoring.

It uses AGS (Architectural Graph System) to classify code into
11 architectural regimes and recommends optimization actions.`,
}

func Execute() error {
	return rootCmd.Execute()
}

func init() {
	rootCmd.PersistentFlags().BoolP("json", "j", false, "Output in JSON format")
	rootCmd.PersistentFlags().BoolP("quiet", "q", false, "Suppress non-essential output")
}
