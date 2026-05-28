.PHONY: setup dev db-up db-down migrate seed clean electron-dev electron-build ios-sync

setup:
	cd backend && python -m venv .venv && .venv/bin/pip install -r requirements.txt
	cd public-site && npm install
	cd admin-app && npm install

dev:
	@echo "Starting backend, public-site, and admin-app..."
	(cd backend && source .venv/bin/activate && uvicorn main:app --reload --port 8000) &
	(cd public-site && npm run dev) &
	(cd admin-app && npm run dev)

db-up:
	docker compose up db redis -d

db-down:
	docker compose down

migrate:
	cd backend && source .venv/bin/activate && alembic upgrade head

seed:
	cd backend && source .venv/bin/activate && python -m app.seed

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete
	rm -rf admin-app/dist admin-app/dist-electron public-site/dist

electron-dev:
	cd admin-app && npm run electron:dev

electron-build:
	cd admin-app && npm run electron:build

ios-sync:
	cd admin-app && npm run build && npx cap sync ios

ios-open:
	cd admin-app && npx cap open ios
