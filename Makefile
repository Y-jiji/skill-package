OPENCODE_DIR := $(HOME)/.config/opencode
CLAUDE_DIR := $(HOME)/.claude
CLAUDE_SETTINGS := $(CLAUDE_DIR)/settings.json

.PHONY: install install-opencode install-claude clean clean-opencode clean-claude

install: install-opencode install-claude

clean: clean-opencode clean-claude

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
	mkdir -p $(CLAUDE_DIR)
	cp _AGENTS.md $(CLAUDE_DIR)/CLAUDE.md
	cp -r skills $(CLAUDE_DIR)/skills
	cp claude-settings.json $(CLAUDE_SETTINGS)

clean-claude:
	rm -f $(CLAUDE_DIR)/CLAUDE.md $(CLAUDE_SETTINGS)
	rm -rf $(CLAUDE_DIR)/skills
