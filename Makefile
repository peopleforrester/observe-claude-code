# ABOUTME: Local→VPS dev loop for the observe-claude-code stack (build host is the netcup VPS).
# ABOUTME: sync pushes the working tree; up/down/test/logs drive Docker Compose over SSH.
VPS        ?= netcup
REMOTE_DIR ?= observe-claude-code
COMPOSE    := docker compose --project-directory . -f compose/docker-compose.yml
REMOTE     := ssh $(VPS) 'export PATH=$$HOME/.local/bin:$$PATH; cd $(REMOTE_DIR) &&

.PHONY: sync up down restart ps logs test clean

# Additive sync only — never deletes on the remote (see no-destructive-sync rule).
sync:
	rsync -az \
	  --exclude '.git' --exclude '.venv' --exclude '__pycache__' \
	  --exclude '**/data' --exclude '*.pyc' \
	  ./ $(VPS):$(REMOTE_DIR)/

up: sync
	$(REMOTE) $(COMPOSE) up -d'

down:
	$(REMOTE) $(COMPOSE) down'

restart: down up

ps:
	$(REMOTE) $(COMPOSE) ps'

logs:
	$(REMOTE) $(COMPOSE) logs --no-color --tail=80'

test: sync
	$(REMOTE) uv run --group dev pytest -v'

# Tear down including named volumes (destructive to stack data only, not source).
clean:
	$(REMOTE) $(COMPOSE) down -v'
