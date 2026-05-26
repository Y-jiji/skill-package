CLAUDE_DIR := $(HOME)/.claude

SETTINGS := claude.json
HOOKS    := $(wildcard hooks/*)
SKILLS   := $(wildcard skills/*)
AGENTS   := $(wildcard agents/*)

.PHONY: install

install:
	@mkdir -p $(CLAUDE_DIR)/hooks
	@mkdir -p $(CLAUDE_DIR)/skills
	@mkdir -p $(CLAUDE_DIR)/agents
	install -m 0644 _AGENTS.md $(CLAUDE_DIR)/CLAUDE.md
	install -m 0644 $(SETTINGS) $(CLAUDE_DIR)/settings.json
	install -m 0755 $(HOOKS)    $(CLAUDE_DIR)/hooks
	@for s in $(SKILLS); do\
		echo "INSTALL $$s"; \
		rm -rf $(CLAUDE_DIR)/skills/$$(basename $$s); \
		cp -r $$s $(CLAUDE_DIR)/skills/; \
	done
	@for a in $(AGENTS); do\
		echo "INSTALL $$a"; \
		install -m 0644 $$a $(CLAUDE_DIR)/agents/; \
	done
