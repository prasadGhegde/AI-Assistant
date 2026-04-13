VOICE_INPUT ?= output/audio/test_radio_echo_strong1.mp3
MUSIC_INPUT ?= assets/audio/jarvis_proper_8min.wav
AUDIO_TEST_OUTPUT ?= output/audio/test_radio_echo_strong1_with_music_custom.mp3
VOICE_VOLUME ?= 1.85
MUSIC_VOLUME ?= 0.12
COMP_THRESHOLD ?= -30
COMP_RATIO ?= 6
COMP_ATTACK ?= 5
COMP_RELEASE ?= 100
COMP_MAKEUP ?= 8
EQ_PRESENCE_FREQ ?= 2200
EQ_PRESENCE_GAIN ?= 4
EQ_HIGH_FREQ ?= 4200
EQ_HIGH_GAIN ?= 3

.PHONY: setup briefing dashboard test install-launchd unload-launchd audio_test

setup:
	python3 -m venv .venv
	. .venv/bin/activate && pip install --upgrade pip && pip install -e .

briefing:
	. .venv/bin/activate && python3 -m morning_briefs run --play

dashboard:
	. .venv/bin/activate && python3 -m morning_briefs dashboard

test:
	. .venv/bin/activate && python -m unittest discover -s tests

audio_test:
	. .venv/bin/activate && python3 scripts/audio_test.py \
		--voice-input "$(VOICE_INPUT)" \
		--music-input "$(MUSIC_INPUT)" \
		--output "$(AUDIO_TEST_OUTPUT)" \
		--voice-volume "$(VOICE_VOLUME)" \
		--music-volume "$(MUSIC_VOLUME)" \
		--compressor-threshold "$(COMP_THRESHOLD)" \
		--compressor-ratio "$(COMP_RATIO)" \
		--compressor-attack "$(COMP_ATTACK)" \
		--compressor-release "$(COMP_RELEASE)" \
		--compressor-makeup "$(COMP_MAKEUP)" \
		--eq-presence-freq "$(EQ_PRESENCE_FREQ)" \
		--eq-presence-gain "$(EQ_PRESENCE_GAIN)" \
		--eq-high-freq "$(EQ_HIGH_FREQ)" \
		--eq-high-gain "$(EQ_HIGH_GAIN)"

install-launchd:
	./scripts/install_launchd.sh

unload-launchd:
	launchctl unload "$$HOME/Library/LaunchAgents/com.prasad.morningbriefs.plist" || true
