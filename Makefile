OPENCODE_DIR := $(HOME)/.config/opencode
CLAUDE_DIR := $(HOME)/.claude
CLAUDE_SETTINGS := $(CLAUDE_DIR)/settings.json
CODEX_DIR := $(HOME)/.codex

.PHONY: install install-opencode install-claude install-codex clean clean-opencode clean-claude clean-codex

install: install-opencode install-claude install-codex

clean: clean-opencode clean-claude clean-codex

# --- opencode ---

install-opencode:
	mkdir -p $(OPENCODE_DIR)
	cp _AGENTS.md $(OPENCODE_DIR)/AGENTS.md
	cp -r skills $(OPENCODE_DIR)/

clean-opencode:
	rm -f $(OPENCODE_DIR)/AGENTS.md
	rm -rf $(OPENCODE_DIR)/skills

# --- claude code ---

install-claude:
	mkdir -p $(CLAUDE_DIR)/hooks
	cp _AGENTS.md $(CLAUDE_DIR)/CLAUDE.md
	cp -r skills $(CLAUDE_DIR)/skills
	cp -r hooks/ $(CLAUDE_DIR)/hooks/
	cp claude-settings.json $(CLAUDE_SETTINGS)

clean-claude:
	rm -f $(CLAUDE_DIR)/CLAUDE.md $(CLAUDE_SETTINGS)
	rm -rf $(CLAUDE_DIR)/skills $(CLAUDE_DIR)/hooks

# --- codex-cli ---

install-codex:
	mkdir -p $(CODEX_DIR)
	cp _AGENTS.md $(CODEX_DIR)/AGENTS.md
	cp -r skills $(CODEX_DIR)/

clean-codex:
	rm -f $(CODEX_DIR)/AGENTS.md
	rm -rf $(CODEX_DIR)/skills
