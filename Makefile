SKILLS_DIR := $(HOME)/.claude/skills

SKILL_NAMES := data-struct

.PHONY: install clean $(addprefix install-,$(SKILL_NAMES)) $(addprefix clean-,$(SKILL_NAMES))

install: $(addprefix install-,$(SKILL_NAMES))

clean: $(addprefix clean-,$(SKILL_NAMES))

install-%:
	mkdir -p $(SKILLS_DIR)/$*
	cp -r skills/$*/* $(SKILLS_DIR)/$*/

clean-%:
	rm -rf $(SKILLS_DIR)/$*
