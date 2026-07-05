package tui

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/bubbles/table"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
	"github.com/Maycon-BertolzoDOTCOM/PyLens/cmd/pylens/analyzer"
	"github.com/Maycon-BertolzoDOTCOM/PyLens/cmd/pylens/github"
)

var (
	titleStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(lipgloss.Color("#FAFAFA")).
			Background(lipgloss.Color("#7D56F4")).
			Padding(0, 1)

	regimeStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(lipgloss.Color("#FF6B6B"))

	successStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#00B894"))

	warningStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#FDCB6E"))

	errorStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#E17055"))

	helpStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#636E72"))
)

type model struct {
	results    []analyzer.Result
	prData     *github.PRData
	table      table.Model
	selected   int
	width      int
	height     int
	quitting   bool
	overallRegime string
}

func initialModel(results []analyzer.Result, prData *github.PRData) model {
	columns := []table.Column{
		{Title: "File", Width: 40},
		{Title: "Regime", Width: 15},
		{Title: "Coupling", Width: 10},
		{Title: "Cohesion", Width: 10},
		{Title: "Decision", Width: 15},
	}

	var rows []table.Row
	for _, r := range results {
		rows = append(rows, table.Row{
			r.FilePath,
			r.Regime,
			fmt.Sprintf("%.2f", r.CouplingIndex),
			fmt.Sprintf("%.2f", r.CohesionIndex),
			r.Decision,
		})
	}

	t := table.New(
		table.WithColumns(columns),
		table.WithRows(rows),
		table.WithFocused(true),
		table.WithHeight(10),
	)

	s := table.DefaultStyles()
	s.Header = s.Header.
		BorderStyle(lipgloss.NormalBorder()).
		BorderForeground(lipgloss.Color("240")).
		Bold(false)
	s.Selected = s.Selected.
		Foreground(lipgloss.Color("229")).
		Background(lipgloss.Color("57")).
		Bold(false)
	t.SetStyles(s)

	return model{
		results:    results,
		prData:     prData,
		table:      t,
		overallRegime: analyzer.GetOverallRegime(results),
	}
}

func (m model) Init() tea.Cmd {
	return nil
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch msg.String() {
		case "q", "ctrl+c":
			m.quitting = true
			return m, tea.Quit
		case "enter":
			// Show details for selected file
			return m, nil
		}
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
	}

	var cmd tea.Cmd
	m.table, cmd = m.table.Update(msg)
	return m, cmd
}

func (m model) View() string {
	if m.quitting {
		return ""
	}

	var sb strings.Builder

	// Header
	sb.WriteString(titleStyle.Render(" PyLens Architectural Review "))
	sb.WriteString("\n\n")

	// PR info
	if m.prData != nil {
		sb.WriteString(fmt.Sprintf("PR: #%d %s\n", m.prData.Number, m.prData.Title))
		sb.WriteString(fmt.Sprintf("Author: %s\n\n", m.prData.Author))
	}

	// Overall regime
	sb.WriteString("Overall Regime: ")
	switch {
	case strings.Contains(m.overallRegime, "PERFECT") || strings.Contains(m.overallRegime, "MODULAR"):
		sb.WriteString(successStyle.Render(m.overallRegime))
	case strings.Contains(m.overallRegime, "COUPLED") || strings.Contains(m.overallRegime, "MIXED"):
		sb.WriteString(warningStyle.Render(m.overallRegime))
	default:
		sb.WriteString(errorStyle.Render(m.overallRegime))
	}
	sb.WriteString("\n\n")

	// Table
	sb.WriteString(m.table.View())
	sb.WriteString("\n")

	// Help
	sb.WriteString(helpStyle.Render("j/k: navigate • enter: details • q: quit"))
	sb.WriteString("\n")

	return sb.String()
}

// RunReview starts the TUI review
func RunReview(results []analyzer.Result, prData *github.PRData) error {
	p := tea.NewProgram(initialModel(results, prData))
	_, err := p.Run()
	return err
}
