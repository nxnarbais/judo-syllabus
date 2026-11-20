PORT ?= 8000
HOST ?= 0.0.0.0
PYTHON ?= /usr/bin/python3
PROJECT_DIR := $(CURDIR)

PID_FILE := /tmp/judo-syllabus.pid
LOG_FILE := /tmp/judo-syllabus.log
ERR_FILE := /tmp/judo-syllabus.err

PLIST_LABEL := com.judo.syllabus
PLIST_PATH := $(HOME)/Library/LaunchAgents/$(PLIST_LABEL).plist
GUI_DOMAIN := gui/$(shell id -u)

.DEFAULT_GOAL := help
.PHONY: help start stop restart status logs validate install-service uninstall-service

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

start: ## Start the server in the background (detached from terminal)
	@if [ -f "$(PID_FILE)" ] && kill -0 $$(cat "$(PID_FILE)") 2>/dev/null; then \
		echo "Server already running (PID $$(cat "$(PID_FILE)")) on http://localhost:$(PORT)"; \
	else \
		nohup $(PYTHON) -m http.server $(PORT) --bind $(HOST) --directory "$(PROJECT_DIR)" > "$(LOG_FILE)" 2>&1 < /dev/null & \
		echo $$! > "$(PID_FILE)"; \
		sleep 0.3; \
		if kill -0 $$(cat "$(PID_FILE)") 2>/dev/null; then \
			echo "Server started (PID $$(cat "$(PID_FILE)")) -> http://localhost:$(PORT)"; \
		else \
			echo "Failed to start server. Check $(LOG_FILE)"; \
			rm -f "$(PID_FILE)"; \
			exit 1; \
		fi; \
	fi

stop: ## Stop the background server
	@if [ -f "$(PID_FILE)" ]; then \
		PID=$$(cat "$(PID_FILE)"); \
		if kill -0 "$$PID" 2>/dev/null; then \
			kill "$$PID" && echo "Stopped server (PID $$PID)"; \
		else \
			echo "Server was not running (stale PID file removed)"; \
		fi; \
		rm -f "$(PID_FILE)"; \
	else \
		echo "No PID file found at $(PID_FILE)"; \
	fi

restart: stop start ## Restart the background server

status: ## Check whether the server is running
	@if [ -f "$(PID_FILE)" ] && kill -0 $$(cat "$(PID_FILE)") 2>/dev/null; then \
		echo "Running (PID $$(cat "$(PID_FILE)")) -> http://localhost:$(PORT)"; \
	elif lsof -iTCP:$(PORT) -sTCP:LISTEN -t >/dev/null 2>&1; then \
		echo "Port $(PORT) is in use (PID $$(lsof -iTCP:$(PORT) -sTCP:LISTEN -t | head -n1))"; \
	else \
		echo "Not running"; \
	fi

logs: ## Tail server logs
	@tail -n 50 -f "$(LOG_FILE)"

validate: ## Validate syllabus.json
	@$(PYTHON) scripts/validate_syllabus.py

install-service: ## Install and start a macOS LaunchAgent (auto-starts on login)
	@mkdir -p "$(HOME)/Library/LaunchAgents"
	@printf '%s\n' \
		'<?xml version="1.0" encoding="UTF-8"?>' \
		'<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">' \
		'<plist version="1.0">' \
		'<dict>' \
		'  <key>Label</key>' \
		'  <string>$(PLIST_LABEL)</string>' \
		'  <key>ProgramArguments</key>' \
		'  <array>' \
		'    <string>$(PYTHON)</string>' \
		'    <string>-m</string>' \
		'    <string>http.server</string>' \
		'    <string>$(PORT)</string>' \
		'    <string>--bind</string>' \
		'    <string>$(HOST)</string>' \
		'  </array>' \
		'  <key>WorkingDirectory</key>' \
		'  <string>$(PROJECT_DIR)</string>' \
		'  <key>RunAtLoad</key>' \
		'  <true/>' \
		'  <key>KeepAlive</key>' \
		'  <true/>' \
		'  <key>StandardOutPath</key>' \
		'  <string>$(LOG_FILE)</string>' \
		'  <key>StandardErrorPath</key>' \
		'  <string>$(ERR_FILE)</string>' \
		'</dict>' \
		'</plist>' > "$(PLIST_PATH)"
	@-launchctl bootout "$(GUI_DOMAIN)" "$(PLIST_PATH)" 2>/dev/null || true
	@launchctl bootstrap "$(GUI_DOMAIN)" "$(PLIST_PATH)"
	@echo "Installed and started LaunchAgent at $(PLIST_PATH) -> http://localhost:$(PORT)"

uninstall-service: ## Stop and remove the macOS LaunchAgent
	@-launchctl bootout "$(GUI_DOMAIN)" "$(PLIST_PATH)" 2>/dev/null || true
	@rm -f "$(PLIST_PATH)"
	@echo "Removed LaunchAgent $(PLIST_PATH)"
