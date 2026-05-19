CLAUDE_DIR   := $(HOME)/.claude

SETTINGS := claude.json
HOOKS    := $(wildcard hooks/*)
SKILLS   := $(wildcard skills/*)

.PHONY: install

install:
	@mkdir -p $(CLAUDE_DIR)/hooks
	@mkdir -p $(CLAUDE_DIR)/skills
	install -m 0644 _AGENTS.md $(CLAUDE_DIR)/CLAUDE.md
	install -m 0644 $(SETTINGS) $(CLAUDE_DIR)/settings.json
	install -m 0755 $(HOOKS)    $(CLAUDE_DIR)/hooks
	@for s in $(SKILLS); do\
		echo "INSTALL $$s"; \
		rm -rf $(CLAUDE_DIR)/skills/$$(basename $$s); \
        	cp -r $$s $(CLAUDE_DIR)/skills/; \
	done
