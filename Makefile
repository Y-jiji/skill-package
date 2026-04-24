OPENCODE_DIR := $(HOME)/.config/opencode
SKILLS_DIR := $(OPENCODE_DIR)/skills

SKILL_NAMES := data-struct lang-rust lang-cuda-cpp

.PHONY: install clean install-agents-md clean-agents-md install-data-struct clean-data-struct install-lang-rust clean-lang-rust install-lang-cuda-cpp clean-lang-cuda-cpp

install: install-agents-md install-data-struct install-lang-rust install-lang-cuda-cpp

clean: clean-agents-md clean-data-struct clean-lang-rust clean-lang-cuda-cpp

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
