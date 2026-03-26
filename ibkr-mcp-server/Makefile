.PHONY: help gateway gateway-down server server-down restart logs logs-gateway logs-server ps lint fmt

GATEWAY_COMPOSE := docker-compose.gateway.yaml
SERVER_COMPOSE  := docker-compose.yaml

# Default: show help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-18s %s\n", $$1, $$2}'

# ── Gateway (long-lived, run once) ──────────────────────────────────────────

gateway: ## Start the IB Gateway container (run once; survives server restarts)
	podman compose -f $(GATEWAY_COMPOSE) up -d

gateway-down: ## Stop and remove the IB Gateway container
	podman compose -f $(GATEWAY_COMPOSE) down

# ── MCP Server (iterate freely) ─────────────────────────────────────────────

server: ## Build and start the MCP server
	podman compose -f $(SERVER_COMPOSE) up --build -d

server-down: ## Stop and remove the MCP server
	podman compose -f $(SERVER_COMPOSE) down

restart: server-down server ## Rebuild and restart the MCP server

# ── Logs ────────────────────────────────────────────────────────────────────

logs: ## Tail logs from both containers
	podman logs -f --names \
		$(shell podman ps -q --filter name=ib-gateway) \
		$(shell podman ps -q --filter name=ibkr-mcp-server) 2>&1

logs-gateway: ## Tail IB Gateway logs
	podman logs -f $(shell podman ps -q --filter name=ib-gateway)

logs-server: ## Tail MCP server logs
	podman logs -f $(shell podman ps -q --filter name=ibkr-mcp-server_ibkr-mcp-server)

# ── Status ───────────────────────────────────────────────────────────────────

ps: ## Show running containers and health
	podman ps --filter name=ib-gateway --filter name=ibkr-mcp-server \
		--format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# ── Dev ──────────────────────────────────────────────────────────────────────

lint: ## Run ruff linter
	uv run ruff check .

fmt: ## Run ruff formatter
	uv run ruff format .
