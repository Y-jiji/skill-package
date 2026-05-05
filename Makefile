OPENCODE_DIR := $(HOME)/.config/opencode
SKILLS_DIR := $(OPENCODE_DIR)/skills
CLAUDE_DIR := $(HOME)/.claude
CLAUDE_SETTINGS := $(CLAUDE_DIR)/settings.json

SKILL_NAMES := data-struct algorithm-dp algorithm-graphs algorithm-sorting-searching lang-rust lang-cuda-cpp

.PHONY: install clean install-agents-md clean-agents-md install-data-struct clean-data-struct install-algorithm-dp clean-algorithm-dp install-algorithm-graphs clean-algorithm-graphs install-algorithm-sorting-searching clean-algorithm-sorting-searching install-lang-rust clean-lang-rust install-lang-cuda-cpp clean-lang-cuda-cpp install-claude-settings clean-claude-settings

install: install-agents-md install-data-struct install-algorithm-dp install-algorithm-graphs install-algorithm-sorting-searching install-lang-rust install-lang-cuda-cpp install-claude-settings

clean: clean-agents-md clean-data-struct clean-algorithm-dp clean-algorithm-graphs clean-algorithm-sorting-searching clean-lang-rust clean-lang-cuda-cpp clean-claude-settings

install-agents-md:
	mkdir -p $(OPENCODE_DIR)
	cp _AGENTS.md $(OPENCODE_DIR)/AGENTS.md

clean-agents-md:
	rm -f $(OPENCODE_DIR)/AGENTS.md

install-data-struct:
	mkdir -p $(SKILLS_DIR)/data-struct
	cp -r skills/data-struct/* $(SKILLS_DIR)/data-struct/

clean-data-struct:
	rm -rf $(SKILLS_DIR)/data-struct

install-algorithm-dp:
	mkdir -p $(SKILLS_DIR)/algorithm-dp
	cp -r skills/algorithm-dp/* $(SKILLS_DIR)/algorithm-dp/

clean-algorithm-dp:
	rm -rf $(SKILLS_DIR)/algorithm-dp

install-algorithm-graphs:
	mkdir -p $(SKILLS_DIR)/algorithm-graphs
	cp -r skills/algorithm-graphs/* $(SKILLS_DIR)/algorithm-graphs/

clean-algorithm-graphs:
	rm -rf $(SKILLS_DIR)/algorithm-graphs

install-algorithm-sorting-searching:
	mkdir -p $(SKILLS_DIR)/algorithm-sorting-searching
	cp -r skills/algorithm-sorting-searching/* $(SKILLS_DIR)/algorithm-sorting-searching/

clean-algorithm-sorting-searching:
	rm -rf $(SKILLS_DIR)/algorithm-sorting-searching

install-lang-rust:
	mkdir -p $(SKILLS_DIR)/lang-rust
	cp -r skills/lang-rust/* $(SKILLS_DIR)/lang-rust/

clean-lang-rust:
	rm -rf $(SKILLS_DIR)/lang-rust

install-lang-cuda-cpp:
	mkdir -p $(SKILLS_DIR)/lang-cuda-cpp
	cp -r skills/lang-cuda-cpp/* $(SKILLS_DIR)/lang-cuda-cpp/

clean-lang-cuda-cpp:
	rm -rf $(SKILLS_DIR)/lang-cuda-cpp

install-claude-settings:
	mkdir -p $(CLAUDE_DIR)
	@if [ -s $(CLAUDE_SETTINGS) ]; then \
		jq -s '.[0] * .[1]' $(CLAUDE_SETTINGS) claude-settings.json > $(CLAUDE_SETTINGS).tmp \
			&& mv $(CLAUDE_SETTINGS).tmp $(CLAUDE_SETTINGS); \
	else \
		cp claude-settings.json $(CLAUDE_SETTINGS); \
	fi

clean-claude-settings:
	@if [ -s $(CLAUDE_SETTINGS) ]; then \
		jq 'del(.model, ."$$schema")' $(CLAUDE_SETTINGS) > $(CLAUDE_SETTINGS).tmp \
			&& mv $(CLAUDE_SETTINGS).tmp $(CLAUDE_SETTINGS); \
	fi
