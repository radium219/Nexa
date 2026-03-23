\# Nexa — Your Assistant from the Future



Look, I'm not going to pretend this is some polished corporate product with a marketing team behind it. It's not. It's a personal AI assistant I built because I wanted something that actually works the way I think — fast, voice-first, and doesn't make me alt-tab out of whatever I'm doing.



Nexa listens for your voice, talks back, searches the web, opens apps, controls your desktop, and can literally see your screen. It runs locally (mostly), it's fast (enough), and it doesn't judge you for asking it to open YouTube at 3am.



\---



\## What it can do



\- Wake word activation — say "hey nexa"(by default) and it's good to go!

\- Voice input with smart silence detection (no more pressing buttons)

\- Natural TTS with Ryan Neural voice — actually sounds decent

\- Web search via DuckDuckGo — real answers, not hallucinations

\- Open any application by name

\- Play YouTube videos

\- Desktop agent — click things, type text, analyze your screen

\- Screen highlighting — it'll point out what you're looking at

\- Conversation memory — it remembers what you said earlier in the session



\---



\## What you need



\- Python 3.11

\- An x.ai API key (for Grok) — get one at \[x.ai/console](https://x.ai/console)

\- A Google Gemini API key (for screen vision) — get one at \[aistudio.google.com](https://aistudio.google.com)

\- A microphone

\- Internet connection (for the AI part, obviously)



\---



\## Setup



Clone the repo, create a `.env` file in the root folder with this:



```

XAI\_API\_KEY=your\_xai\_key\_here

GEMINI\_API\_KEY=your\_gemini\_key\_here

```



Then:



```bash

python -m venv venv

venv\\Scripts\\activate

pip install -r requirements.txt

python core/nexa\_gui.py

```



That's it. No wizard, no installer, no nonsense. Just run it.



\---



\## Project structure



```

project nexa/

├── .env              ← your API keys, don't share this

├── requirements.txt

└── core/

&#x20;   ├── nexa\_gui.py   ← the interface

&#x20;   └── nexa\_core.py  ← the brain

```



\---



\## Versioning



I use a three-part version system: `vX.X.X`



\- First number: major milestones that I'm genuinely proud of (Its 1 becouse there is none FOR NOW!)

\- Second number: meaningful new features

\- Third number: shame versions that ı genuenly HATE and try to keep a secret, mostly bugfix



Current version: \*\*v1.11.7\*\*



\---



\## Known issues



\- First startup takes a while because Whisper model loads on CPU.YES I KNOW İTS FEW TİMES FASTER ON GPUS. but not my GTX750Tİ, so ı set it for cpu, if you got a beefy gpu and want it to load fast, that sounds like a you problem.

\- Screen highlighting works best on single-monitor setups (ı couldn't figure it out, my bad)

\- If Nexa says something that starts with asterisks, blame Grok, not me



\---



\## Why does this exist



I wanted REAL assistent just like jarvis. Not a chatbot, not a widget, not a voice assistant that needs 5 taps to do anything. Just something I can talk to while I'm gaming or working and it actually does things. So I built it.



It's a work in progress. Always will be, probably.



if you find any bugs, then ı don't give a sh1t -Radium219







jk jk, report the bugs -still Radium219

