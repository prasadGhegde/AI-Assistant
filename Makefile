.PHONY: setup briefing dashboard test install-launchd unload-launchd

setup:
	python3 -m venv .venv
	. .venv/bin/activate && pip install --upgrade pip && pip install -e .

briefing:
	. .venv/bin/activate && python3 -m morning_briefs run --play

dashboard:
	. .venv/bin/activate && python3 -m morning_briefs dashboard

test:
	python3 -m unittest discover -s tests

install-launchd:
	./scripts/install_launchd.sh

unload-launchd:
	launchctl unload "$$HOME/Library/LaunchAgents/com.prasad.morningbriefs.plist" || true
