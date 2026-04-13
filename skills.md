# Morning Briefs Skills

This file defines the product behavior that every Morning Briefs run should preserve.

## Briefing Flow

Weather is an official part of the morning briefing flow. The sequence is:

1. Premium tactical intro: "Good day, Captain. Welcome to the briefing for Operation Daybreak."
2. Weather with current temperature, conditions, one useful carry/wear tip, and rain, wind, or sun cautions only when relevant.
3. Geopolitics.
4. Technology and AI.
5. Stock market.
6. Watch list for today.
7. Closing question with a silent 10-second typed follow-up window.

The flow should feel woven together, not like disconnected blocks. Transitions should be smooth, brief, and natural. Structural headings are for Markdown and dashboard synchronization only; they must not be spoken as phrases.

## Source Quality

Use high-quality sources and favor consequential, factual reporting with direct relevance to a work morning. Prefer primary, institutional, specialist, or market-moving sources. Prioritize events from the last 24 hours, and use exact dates when relevant.

Good-news-only mode is the default. Prefer positive, constructive, promising, forward-looking, useful developments: de-escalation, diplomacy, approvals, breakthroughs, investment, strong demand, earnings beats, useful partnerships, and resilient market signals. The result should feel smart and energizing, not fluffy.

Reject or heavily down-rank:

- Celebrity, gossip, relationship, entertainment, or influencer stories.
- Person-versus-person commentary unless it has direct geopolitical, technological, or financial significance.
- Opinion-heavy pieces without hard news value.
- Low-value reaction articles.
- Vague trend summaries without a concrete development.
- Filler roundups and SEO explainers when better source material exists.
- Gloomy, doom-heavy, depressing, panic-driven, or bad-news-only stories.

Keep raw source data with quality scores and rejection reasons so the filter can be tuned later.

## Speaking Style

The assistant should sound premium, energetic, cinematic, conversational, and useful. Use the OpenAI TTS Ryan system voice for the narrated briefing when available: greeting, weather, news, watch list, and the spoken closing question. Follow-up answers are now typed in the dashboard rather than spoken because microphone handoff was unreliable. Aim for a warm, intelligent, well-mannered morning assistant with a lightly British cadence when the selected voice supports it. Do not imitate, name, or clone any copyrighted character or protected voice.

If the provider/runtime rejects Ryan, retry the whole clip with the configured fallback voice and record a warning. Do not mix voices inside one session unless a technical failure makes fallback unavoidable.

The script should be concise but alive: more rhythm, more presence, fewer generic phrases, and no AI filler. It should feel like a sharp assistant speaking over coffee, not a robotic news reader.

Avoid:

- Spoken labels such as "Morning Brief", "Geopolitical news", or "Technology news".
- Slide-deck transitions.
- "Why this matters" followed by "this is important because".
- Formulaic section announcements.

Explain implications naturally inside the sentence flow.

## Narration Tone

The narration should feel like a premium AI mission-control assistant: cinematic, calm, sharp, authoritative, polished, and well-mannered. It may have subtle robotic texture in the audio post-processing, but the language must remain clear, adult, useful, and never gimmicky. The assistant should not imitate, name, or clone any copyrighted character or protected voice.

## Narration Rules

- The LLM must not freely invent the greeting, operation name, section transitions, closing, or final question.
- The opening, transitions, watchlist intro, closing, and final question must be assembled from curated phrase banks.
- The content body can remain flexible, but it must fit inside the fixed briefing structure.
- Select only one phrase from each phrase-bank category per run.
- Avoid repeating the same phrase inside a single briefing.
- Avoid reusing the same greeting, operation name, and closing too frequently across recent runs when history is available.
- The selected phrases must combine coherently; do not mix playful, goofy, or overdramatic lines with the premium tactical tone.
- Weighted randomization is allowed later by converting a phrase-bank entry from a string to an object with `text` and `weight`.

## Briefing Structure

Every run should follow this stable spoken structure while still sounding human and freshly written:

1. Tactical greeting: `{greeting} {intro_template}` using the selected `{operation_name}`.
2. Intro line: one approved sentence that frames the morning without recapping the whole brief.
3. Weather transition and weather: current conditions, temperature, and one practical carry/wear note in 20 to 25 seconds.
4. Geopolitics transition and body: factual, constructive, source-backed developments with a practical implication.
5. Technology and AI transition and body: substance over spectacle, focused on platforms, models, deployment, policy, compute, security, and useful momentum.
6. Market transition and body: constructive market signals, leadership, breadth, earnings, rates, or watchable positioning without panic framing.
7. Watchlist intro and watchlist: a short set of concrete threads to revisit, not a repeated summary.
8. Closing and final question: one concise closing line plus one concise question, then stop speaking.

## Phrase Banks

The runtime source of truth is `config/narration_phrases.json`. Add new approved lines there so the system can extend without business logic changes.

Greetings:

- Good day, Captain.
- Good morning, Captain.
- Greetings, Captain.
- Captain, welcome back.
- Good to see you, Captain.

Operation Names:

- Operation Daybreak
- Operation Morning Star
- Operation First Light
- Operation Dawn Watch
- Operation Sunrise Protocol

Intro Templates:

- Welcome to the debriefing of `{operation_name}`.
- You are now entering the debriefing for `{operation_name}`.
- Initiating morning debrief for `{operation_name}`.
- This is your morning briefing for `{operation_name}`.

Weather Transitions:

- First, a quick read on the conditions outside.
- Before the intelligence pass, a practical look at the weather.
- We will start with the outside conditions, then move into the signal.
- First checkpoint: weather, kit, and movement.

Geopolitics Transitions:

- Now to the global front, where the useful signal is diplomatic and operational.
- The first intelligence pane is global, with emphasis on constructive movement.
- On the geopolitical board, the strongest signal is the one with practical follow-through.
- Turning to the world stage, the focus is on developments that can shape the workday.

Technology Transitions:

- The technology pane is next, with AI signal separated from noise.
- On the technology front, I am watching the developments most likely to affect decisions.
- The next pass is technology and AI, filtered for substance over spectacle.
- Now to the AI and platform layer, where practical momentum matters most.

Market Transitions:

- The market board comes into view next, with attention on constructive risk signals.
- For markets, the useful read is leadership, breadth, and what may carry into the open.
- The financial pane is next, focused on signals that can shape positioning.
- Now to the market front, where price action is useful only when the signal has depth.

Watchlist Intros:

- For the watch list, keep these operational threads close.
- Before we close, these are the threads worth revisiting today.
- Your watch list is short and practical.
- These are the items I would keep on the console through midday.

Closings:

- That concludes today's debrief, Captain.
- Mission briefing complete, Captain.
- This concludes your morning operational summary.
- Debrief complete. You are cleared for the day.

Final Questions:

- Any questions on the operation, Captain?
- Would you like a deeper look at any front, Captain?
- Any area you would like me to expand on, Captain?
- Do you want a follow-up on any item from today's briefing?

## Randomization Rules

The system should pick one approved phrase from each bank, assemble the modular opening and section transitions, and persist the selected plan in the script metadata. If `data/narration_history.json` exists, the selector should avoid recent reuse across protected banks, especially greetings, operation names, transitions, closings, and final questions. If all entries in a protected bank were used recently, the selector may reuse one rather than inventing a new phrase.

## Future Extension Notes

To add more approved variation, append lines to `config/narration_phrases.json` under the appropriate bank. Keep additions premium, concise, tactical, and composable with every operation name. Do not add lines that depend on a specific story, market condition, weather condition, or private context unless the code also adds safe selection rules for that context.

## Weather Tone

Weather should feel cheerful, playful, joyful, smooth, and premium. It still needs practical information, but it must stay tight: 20 to 25 seconds, a bright summary, one useful carry/wear hint, and a graceful move into the day.

## Visual Sync

The browser must be visibly open while narration is happening. The screen-state flow is:

1. Greeting screen.
2. Weather screen.
3. News screen.
4. Typed follow-up/timeout screen.

During speech, the dashboard should:

- Smoothly scroll to the active section.
- Transition between screen states, not sit as one static page.
- Highlight the active section and active topic.
- Use the real browser audio element time for the primary presentation sync.
- Run visual sync from animation frames during playback so the left progress rail and active clipping do not lag behind audio.
- Build cue proportions from actual script section word counts, not large fixed category blocks, then scale those proportions to the real MP3 duration once audio metadata is available.
- Progress from intro to weather to news to watch list to closing.
- Avoid jumpy motion.
- Keep visual focus aligned with the narration timeline.
- Keep all narration-supporting cards readable with complete sentences. Do not truncate key story text with ellipses; resize, reflow, or scroll secondary stacks instead.
- Make the left progress rail obvious: active stage, live phase progress, and completed stages should be visually distinct and tied to actual audio playback with only a tiny visual lead to offset animation latency.
- Use a subtle animated glow, edge sweep, or pulse on the active clipping/card while Ryan is speaking so the user can immediately see what is being narrated.
- Launch Chrome directly into kiosk fullscreen presentation mode with an isolated per-run Chrome profile so existing browser sessions cannot ignore presentation flags.
- When macOS accessibility permissions allow it, request native Chrome fullscreen and temporarily hide `View > Always Show Toolbar in Full Screen`, then restore that toolbar setting when the session closes.
- Animate the assistant icon during greeting, narration, and transitions.
- Avoid low-value decorative visuals such as confusing heat maps; prioritize active-story focus, story hierarchy, useful market context, and clear guidance.

If browser audio autoplay is blocked, show a clear start control and sync from actual audio playback after the user starts Ryan. The `afplay` path is allowed only as an explicit fallback because it cannot provide the same real-time browser sync.

## Music

Use the uploaded local WAV file at `assets/audio/jarvis_proper_8min.wav` during the session. It should be audible but restrained, energetic and premium, and duck under Ryan's narration. The browser music layer should work even when the MP3 mix cannot be produced. When `ffmpeg` is available, mix the same WAV into the MP3 with sidechain ducking. Keep narration under 6 minutes and 20 seconds so the music bed does not end early.

## Voice Effect Presets

The clean OpenAI TTS output must be preserved before voice effects. When voice effects are enabled, render a batch of speech-friendly AI/radio/synthetic variants from the same clean TTS file, then mix each variant with the background music for comparison. The app should play only the configured default preset automatically. Presets should be distinct but intelligible: `clean_ai`, `subtle_assistant`, `jarvis_clean`, `jarvis_like`, `radio_comms`, `tactical_brief`, `hologram`, `synthetic_warm`, `stronger_robot`, `bitcrushed_bot`, and `masked_vocoder_style`.

Save clear artifacts such as `briefing_clean.mp3`, `briefing_voice_03_jarvis_clean.mp3`, and `briefing_voice_03_jarvis_clean_final.mp3`. Also save `original_tts.wav` and `robotic_tts.wav` for quick A/B checks of the clean and selected processed voice.

## End Of Session

At the end, ask only a short tactical question, ideally "Any questions on Operation Daybreak, Captain?", then stop speaking. Do not recap the briefing again. Do not say "I will wait ten seconds." The dashboard opens a typed response box for 10 seconds. Do not start browser speech recognition or microphone listening. If there is a typed question, answer quickly in text inside the dashboard, leave the answer visible briefly, and close the Chrome tab opened for the briefing. If there is no user input, close gracefully without trying to synthesize a final spoken clip.

> I will assume there is nothing else for now. Have a great day, Prasad.
