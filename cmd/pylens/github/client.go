package github

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"strings"
	"time"
)

// Client wraps GitHub API access via gh CLI
type Client struct {
	token string
}

// NewClient creates a new GitHub client using gh CLI auth
func NewClient() (*Client, error) {
	// Try to get token from gh CLI
	cmd := exec.Command("gh", "auth", "token")
	output, err := cmd.Output()
	if err != nil {
		return nil, fmt.Errorf("not authenticated with gh CLI: %w", err)
	}

	token := strings.TrimSpace(string(output))
	if token == "" {
		return nil, fmt.Errorf("no auth token found")
	}

	return &Client{token: token}, nil
}

// PRData holds PR metadata
type PRData struct {
	Number    int
	Title     string
	Author    string
	Base      string
	Head      string
	Files     []FileData
	CreatedAt time.Time
}

// FileData holds file change info
type FileData struct {
	Path     string
	Status   string // added, modified, removed
	Additions int
	Deletions int
	Patch    string
}

// Comment represents a PR comment
type Comment struct {
	Body      string
	Author    string
	CreatedAt time.Time
}

// FileWithContent holds file data with its content
type FileWithContent struct {
	Path    string
	Status  string
	Content string
}

// ParsePythonFiles extracts Python files and fetches their content
func ParsePythonFiles(files []FileData) []FileWithContent {
	var result []FileWithContent

	for _, f := range files {
		// Only Python files
		if !strings.HasSuffix(f.Path, ".py") {
			continue
		}
		// Skip removed files
		if f.Status == "removed" {
			continue
		}

		// Fetch file content
		cmd := exec.Command("gh", "api",
			fmt.Sprintf("repos/{owner}/{repo}/contents/%s", f.Path),
			"-H", "Accept: application/vnd.github.v3.raw")
		output, err := cmd.Output()
		if err != nil {
			continue
		}

		result = append(result, FileWithContent{
			Path:    f.Path,
			Status:  f.Status,
			Content: string(output),
		})
	}

	return result
}

// GetCurrentPR returns the PR number from GITHUB_REF or gh pr list
func GetCurrentPR() (int, error) {
	// Try GITHUB_REF first (works in Actions)
	ref := os.Getenv("GITHUB_REF")
	if ref != "" {
		// refs/pull/123/merge
		parts := strings.Split(ref, "/")
		for i, part := range parts {
			if part == "pull" && i+1 < len(parts) {
				var prNum int
				fmt.Sscanf(parts[i+1], "%d", &prNum)
				if prNum > 0 {
					return prNum, nil
				}
			}
		}
	}

	// Try gh pr view
	cmd := exec.Command("gh", "pr", "view", "--json", "number")
	output, err := cmd.Output()
	if err != nil {
		return 0, fmt.Errorf("could not determine PR: %w", err)
	}

	var result struct {
		Number int `json:"number"`
	}
	if err := json.Unmarshal(output, &result); err != nil {
		return 0, err
	}

	return result.Number, nil
}

// GetCurrentRepo returns owner/repo from git remote
func GetCurrentRepo() (string, error) {
	cmd := exec.Command("git", "remote", "get-url", "origin")
	output, err := cmd.Output()
	if err != nil {
		return "", fmt.Errorf("could not get remote URL: %w", err)
	}

	url := strings.TrimSpace(string(output))

	// Parse SSH or HTTPS URL
	// SSH: git@github.com:owner/repo.git
	// HTTPS: https://github.com/owner/repo.git
	if strings.Contains(url, "github.com") {
		url = strings.TrimPrefix(url, "https://github.com/")
		url = strings.TrimPrefix(url, "git@github.com:")
		url = strings.TrimSuffix(url, ".git")
		return url, nil
	}

	return "", fmt.Errorf("not a GitHub remote: %s", url)
}

// GetPR fetches PR data including changed files
func (c *Client) GetPR(repo string, prNum int) (*PRData, error) {
	// Get PR metadata
	cmd := exec.Command("gh", "pr", "view", fmt.Sprintf("%d", prNum),
		"--repo", repo,
		"--json", "number,title,author,baseRefName,headRefName,createdAt")
	output, err := cmd.Output()
	if err != nil {
		return nil, fmt.Errorf("failed to fetch PR: %w", err)
	}

	var prMeta struct {
		Number      int    `json:"number"`
		Title       string `json:"title"`
		Author      struct {
			Login string `json:"login"`
		} `json:"author"`
		BaseRefName string    `json:"baseRefName"`
		HeadRefName string    `json:"headRefName"`
		CreatedAt   time.Time `json:"createdAt"`
	}
	if err := json.Unmarshal(output, &prMeta); err != nil {
		return nil, err
	}

	// Get changed files
	cmd = exec.Command("gh", "pr", "diff", fmt.Sprintf("%d", prNum),
		"--repo", repo,
		"--name-status")
	output, err = cmd.Output()
	if err != nil {
		return nil, fmt.Errorf("failed to fetch PR diff: %w", err)
	}

	var files []FileData
	for _, line := range strings.Split(strings.TrimSpace(string(output)), "\n") {
		if line == "" {
			continue
		}
		parts := strings.SplitN(line, "\t", 2)
		if len(parts) < 2 {
			continue
		}

		status := "modified"
		switch parts[0] {
		case "A":
			status = "added"
		case "D":
			status = "removed"
		case "M":
			status = "modified"
		}

		files = append(files, FileData{
			Path:   parts[1],
			Status: status,
		})
	}

	return &PRData{
		Number:    prNum,
		Title:     prMeta.Title,
		Author:    prMeta.Author.Login,
		Base:      prMeta.BaseRefName,
		Head:      prMeta.HeadRefName,
		Files:     files,
		CreatedAt: prMeta.CreatedAt,
	}, nil
}

// PostComment posts a comment to a PR
func (c *Client) PostComment(repo string, prNum int, body string) error {
	cmd := exec.Command("gh", "pr", "comment", fmt.Sprintf("%d", prNum),
		"--repo", repo,
		"--body", body)
	return cmd.Run()
}

// FindExistingReview searches for a previous PyLens review
func (c *Client) FindExistingReview(repo string, prNum int) (*Comment, error) {
	cmd := exec.Command("gh", "api",
		fmt.Sprintf("repos/%s/issues/%d/comments", repo, prNum),
		"--paginate",
		"--jq", ".[] | select(.body | contains(\"PyLens Architectural Review\")) | {body: .body, author: .user.login, created_at: .created_at}")
	output, err := cmd.Output()
	if err != nil {
		return nil, err
	}

	if len(output) == 0 {
		return nil, nil
	}

	// Parse the first match
	lines := strings.SplitN(string(output), "\n", 2)
	if len(lines) == 0 {
		return nil, nil
	}

	return &Comment{
		Body: lines[0],
	}, nil
}
