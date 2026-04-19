CLAUDE_DIR := $(HOME)/.claude
SKILLS_DIR := $(CLAUDE_DIR)/skills

SKILL_NAMES := data-struct

.PHONY: install clean install-claude-md clean-claude-md install-data-struct clean-data-struct

install: install-claude-md install-data-struct

clean: clean-claude-md clean-data-struct

install-claude-md:
	cp _CLAUDE.md $(CLAUDE_DIR)/CLAUDE.md

clean-claude-md:
	rm -f $(CLAUDE_DIR)/CLAUDE.md

install-data-struct:
	mkdir -p $(SKILLS_DIR)/data-struct
	cp -r skills/data-struct/* $(SKILLS_DIR)/data-struct/

clean-data-struct:
	rm -rf $(SKILLS_DIR)/data-struct
