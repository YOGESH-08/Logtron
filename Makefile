# LogScan DFA — Makefile
# High-Performance Log Pattern Analyzer using Regular Expressions and Finite Automata

.PHONY: help venv install run test clean push

# Default target
.DEFAULT_GOAL := help

PYTHON := python
VENV_DIR := venv

ifeq ($(OS),Windows_NT)
	VENV_PYTHON := $(VENV_DIR)\Scripts\python.exe
	VENV_STREAMLIT := $(VENV_DIR)\Scripts\streamlit.exe
	VENV_PYTEST := $(VENV_DIR)\Scripts\pytest.exe
	RM := rmdir /s /q
else
	VENV_PYTHON := $(VENV_DIR)/bin/python
	VENV_STREAMLIT := $(VENV_DIR)/bin/streamlit
	VENV_PYTEST := $(VENV_DIR)/bin/pytest
	RM := rm -rf
endif

help: ## Show this help message
	@echo "LogScan DFA Commands:"
	@echo "--------------------"
	@echo "make venv       - Create Python virtual environment"
	@echo "make install    - Install required dependencies"
	@echo "make run        - Launch Streamlit web dashboard"
	@echo "make test       - Run unit test suite with pytest"
	@echo "make clean      - Clean cache and temporary build files"
	@echo "make push       - Push local commits to remote git repository"

venv: ## Create virtual environment
	$(PYTHON) -m venv $(VENV_DIR)

install: ## Install requirements into virtual environment
	$(VENV_PYTHON) -m pip install -r requirements.txt

run: ## Launch Streamlit application
	$(VENV_STREAMLIT) run app.py

test: ## Run unit tests
	$(VENV_PYTEST) tests/ -v

clean: ## Clean Python cache and build files
	@echo Cleaning cache files...
	-$(RM) __pycache__
	-$(RM) .pytest_cache
	-$(RM) docs\__pycache__

push: ## Push commits to remote origin main
	git push origin main
