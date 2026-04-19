CLAUDE_DIR := $(HOME)/.claude
SKILLS_DIR := $(CLAUDE_DIR)/skills

SKILL_NAMES := data-struct

.PHONY: install clean $(addprefix install-,$(SKILL_NAMES)) $(addprefix clean-,$(SKILL_NAMES))

install: install-claude-md $(addprefix install-,$(SKILL_NAMES))

clean: clean-claude-md $(addprefix clean-,$(SKILL_NAMES))

install-claude-md:
	cp _CLAUDE.md $(CLAUDE_DIR)/CLAUDE.md

clean-claude-md:
	rm -f $(CLAUDE_DIR)/CLAUDE.md

install-%:
	mkdir -p $(SKILLS_DIR)/$*
	cp -r skills/$*/* $(SKILLS_DIR)/$*/

clean-%:
	rm -rf $(SKILLS_DIR)/$*
