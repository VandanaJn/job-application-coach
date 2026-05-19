.DEFAULT_GOAL := help

ifeq ($(OS),Windows_NT)
    VENV_PIP := infra/.venv/Scripts/pip
else
    VENV_PIP := infra/.venv/bin/pip
endif

.PHONY: help bootstrap install-infra synth-dev deploy-dev synth-prod deploy-prod \
        test test-cov lint typecheck \
        install-frontend dev build-frontend test-frontend

help:
	@echo "CDK"
	@echo "  install-infra   Create .venv and install CDK Python dependencies"
	@echo "  bootstrap       Bootstrap CDK in your AWS account (run once)"
	@echo "  synth-dev       Synthesize CloudFormation for dev stack"
	@echo "  deploy-dev      Deploy dev stack to AWS"
	@echo "  synth-prod      Synthesize CloudFormation for prod stack"
	@echo "  deploy-prod     Deploy prod stack to AWS"
	@echo ""
	@echo "Backend"
	@echo "  run             Run API locally (requires .env)"
	@echo "  test            Run backend tests"
	@echo "  test-cov        Run backend tests with coverage"
	@echo "  lint            Run ruff linter"
	@echo "  typecheck       Run mypy on backend and infra"
	@echo ""
	@echo "Frontend"
	@echo "  install-frontend  Install frontend dependencies"
	@echo "  dev               Start frontend dev server"
	@echo "  build-frontend    Build frontend for production"
	@echo "  test-frontend     Run frontend tests"

# CDK
install-infra:
	python -m venv infra/.venv
	$(VENV_PIP) install -r infra/requirements.txt

bootstrap:
	cd infra && cdk bootstrap

synth-dev:
	cd infra && cdk synth JobCoachDev

deploy-dev:
	cd infra && cdk deploy JobCoachDev

synth-prod:
	cd infra && cdk synth JobCoachProd

deploy-prod:
	cd infra && cdk deploy JobCoachProd

# Backend
run:
	python -m uvicorn api.app:app --reload --env-file .env

test:
	python -m pytest

test-cov:
	python -m pytest --cov

lint:
	ruff check .

typecheck:
	mypy .
	cd infra && mypy

# Frontend
install-frontend:
	cd frontend && npm install

dev:
	cd frontend && npm run dev

build-frontend:
	cd frontend && npm run build

test-frontend:
	cd frontend && npm test
