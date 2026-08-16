.PHONY: dev down backend-test frontend-test test api-key-create api-key-list api-key-revoke api-key-create-postgres api-key-list-postgres api-key-revoke-postgres

dev:
	docker compose up --build

down:
	docker compose down

backend-test:
	cd backend && .venv/bin/pytest

frontend-test:
	cd frontend && npm test -- --run

test: backend-test frontend-test

api-key-create:
	cd backend && .venv/bin/python scripts/manage_api_keys.py --file ../.data/api_clients.json create --name "$(NAME)" --rpm $(if $(RPM),$(RPM),10)

api-key-list:
	cd backend && .venv/bin/python scripts/manage_api_keys.py --file ../.data/api_clients.json list

api-key-revoke:
	cd backend && .venv/bin/python scripts/manage_api_keys.py --file ../.data/api_clients.json revoke "$(CLIENT_ID)"

api-key-create-postgres:
	PYTHONPATH=backend backend/.venv/bin/python backend/scripts/manage_api_keys.py --backend postgres create --name "$(NAME)" --rpm $(if $(RPM),$(RPM),10)

api-key-list-postgres:
	PYTHONPATH=backend backend/.venv/bin/python backend/scripts/manage_api_keys.py --backend postgres list

api-key-revoke-postgres:
	PYTHONPATH=backend backend/.venv/bin/python backend/scripts/manage_api_keys.py --backend postgres revoke "$(CLIENT_ID)"
