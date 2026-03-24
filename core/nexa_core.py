"""
NEXA CORE v1.11.8 - Groq + Llama 3.3 70B
UI + desktop agent + web search + app launcher + YouTube

Changelog v1.11.8:
- xai Grok-3 → Groq Llama 3.3 70B (free tier, significantly faster)
- XAI_API_KEY → GROQ_API_KEY

Changelog v1.11.7:
- TTS no longer writes to disk, audio data is generated in RAM (BytesIO) and played directly
- Reduced latency, no temp file cleanup required

Changelog v1.11.6:
- TTS language detection: 5% character ratio threshold instead of single character

Changelog v1.11.5:
- google.generativeai → google.genai, gemini-2.5-flash

Changelog v1.11.4:
- Shutdown command added

Changelog v1.11.3:
- Conversation memory added

Changelog v1.11.2:
- Whisper medium → base

Changelog v1.11.1:
- Grok vision → Gemini Flash vision
"""

import os
import json
import time
import asyncio
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
import random
from dotenv import load_dotenv
from openai import OpenAI
from duckduckgo_search import DDGS
import pywhatkit
import pyaudio
import wave
from io import BytesIO
from faster_whisper import WhisperModel
import torch
import pyautogui
import cv2
import numpy as np
import base64
import tkinter as tk
from tkinter import scrolledtext, Button, Entry, Label, Frame
from threading import Thread
import edge_tts
import pygame

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1

# CONFIG
WAKE_WORD = "hey next"
WHISPER_MODEL_SIZE = "base"
AWAKE = False

# VAD CONFIG
SAMPLE_RATE = 16000
CHUNK_SIZE = 1024
SILENCE_THRESHOLD = 500        # RMS threshold — adjust to your environment (lower = more sensitive)
SILENCE_DURATION = 1.5         # seconds of silence before recording stops
MIN_SPEECH_DURATION = 0.5      # minimum speech duration (noise filter)

# TTS CONFIG - edge-tts voices
TTS_VOICE_EN = "en-GB-RyanNeural"       # English male voice (Jarvis vibe)
TTS_VOICE_TR = "tr-TR-AhmetNeural"      # Turkish male voice

script_dir = Path(__file__).parent
project_root = script_dir.parent
load_dotenv(project_root / ".env")

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
    timeout=60
)

# Gemini Flash — vision operations only
from google import genai as google_genai
gemini_client = google_genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

device = "cuda" if torch.cuda.is_available() else "cpu"
compute_type = "float16" if device == "cuda" else "int8"
whisper_model = WhisperModel(WHISPER_MODEL_SIZE, device=device, compute_type=compute_type)
print("Whisper base ready. GPU:", "Yes 🔥" if device == "cuda" else "CPU mode")

pygame.mixer.init()

# ====================== TOOLS ======================
tools = [
    {"type": "function", "function": {"name": "web_search", "description": "Search the web. Use mode='browser' ONLY when user says 'show me the results for' or 'open the results for'. Otherwise always use mode='search'.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "mode": {"type": "string", "enum": ["search", "browser"], "description": "'search' = search via DDG and respond, 'browser' = open in new browser tab"}}, "required": ["query", "mode"]}}},
    {"type": "function", "function": {"name": "play_on_youtube", "description": "Play on YouTube", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "open_application", "description": "Open any app or game by name using Windows Search", "parameters": {"type": "object", "properties": {"app_name": {"type": "string"}}, "required": ["app_name"]}}},
    {"type": "function", "function": {"name": "desktop_agent", "description": "Desktop control. Actions: type_text, click_description, analyze_screen, highlight_element, search_in_browser, close_current, minimize_current. Use highlight_element when user says 'show me', 'where is', 'point to', 'highlight'. Use analyze_screen when user asks what's on screen.", "parameters": {"type": "object", "properties": {"action": {"type": "string", "enum": ["type_text", "click_description", "analyze_screen", "highlight_element", "search_in_browser", "close_current", "minimize_current"]}, "params": {"type": "object"}}, "required": ["action"]}}}
]

def web_search(query: str, mode: str = "search"):
    if mode == "browser":
        try:
            import webbrowser
            url = "https://duckduckgo.com/?q=" + query.replace(" ", "+")
            webbrowser.open_new_tab(url)
            return f"Opened search results for '{query}' in your browser, sir."
        except Exception as e:
            return f"Couldn't open browser, sir. Error: {e}"
    else:
        try:
            results = DDGS().text(query, max_results=3)
            return "\n".join([f"• {r['title']}\n  {r['href']}\n  {r['body']}" for r in results])
        except:
            return "Search timed out, sir."

def play_on_youtube(query: str):
    try:
        pywhatkit.playonyt(query)
        return f"Playing '{query}', sir."
    except:
        return "Couldn't open YouTube, sir."

def open_application(app_name: str):
    try:
        pyautogui.hotkey("win")
        time.sleep(0.8)
        pyautogui.write(app_name, interval=0.05)
        time.sleep(1.5)
        pyautogui.press("enter")
        return f"Searched and launched '{app_name}', sir."
    except Exception as e:
        return f"Couldn't launch '{app_name}', sir. Error: {e}"

def _screenshot_base64() -> str:
    """Takes a screenshot and returns it as a base64 string."""
    screenshot = pyautogui.screenshot()
    buffer = BytesIO()
    screenshot.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")

def _ask_gemini_vision(image_b64: str, prompt: str) -> str:
    """Sends a screenshot and prompt to Gemini Flash, returns the response."""
    from google.genai import types
    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(data=base64.b64decode(image_b64), mime_type="image/png"),
            prompt
        ]
    )
    return response.text

def show_highlight_overlay(x: int, y: int, w: int, h: int, duration: float = 3.0):
    """
    Opens a transparent overlay on screen and draws a highlight box at the given coordinates.
    No title bar, click-through, auto-closes after duration seconds.
    """
    def _run():
        overlay = tk.Tk()
        overlay.overrideredirect(True)           # no title bar
        overlay.attributes("-topmost", True)     # always on top
        overlay.attributes("-transparentcolor", "black")  # black = transparent
        overlay.attributes("-alpha", 1.0)

        sw = overlay.winfo_screenwidth()
        sh = overlay.winfo_screenheight()
        overlay.geometry(f"{sw}x{sh}+0+0")
        overlay.configure(bg="black")

        canvas = tk.Canvas(overlay, bg="black", highlightthickness=0,
                           width=sw, height=sh)
        canvas.pack()

        # Highlight box — bright green, 3px border
        canvas.create_rectangle(x, y, x + w, y + h,
                                 outline="#00ff9d", width=3)
        # Corner label
        canvas.create_text(x + 5, y - 12, text="Nexa",
                           fill="#00ff9d", font=("Arial", 10, "bold"), anchor="w")

        overlay.after(int(duration * 1000), overlay.destroy)
        overlay.mainloop()

    Thread(target=_run, daemon=True).start()

def desktop_agent(action: str, params: dict = None):
    if params is None:
        params = {}
    try:
        if "delete" in action.lower() or "end task" in action.lower() or "kill" in action.lower():
            return "Restricted action, sir."

        if action == "type_text":
            text = params.get("text", "")
            pyautogui.write(text, interval=0.05)
            return f"Typed '{text}', sir."

        elif action == "click_description":
            desc = params.get("description", "")
            image_b64 = _screenshot_base64()
            sw = pyautogui.size().width
            sh = pyautogui.size().height
            prompt = (
                f"Screen resolution is {sw}x{sh}. "
                f"Find the UI element described as: '{desc}'. "
                f"Return ONLY a JSON object like: {{\"x\": 123, \"y\": 456, \"w\": 100, \"h\": 30}} "
                f"representing the bounding box. No extra text."
            )
            raw = _ask_gemini_vision(image_b64, prompt)
            coords = json.loads(raw.strip())
            cx = coords["x"] + coords["w"] // 2
            cy = coords["y"] + coords["h"] // 2
            show_highlight_overlay(coords["x"], coords["y"], coords["w"], coords["h"], duration=1.5)
            time.sleep(0.3)
            pyautogui.moveTo(cx, cy)
            pyautogui.click()
            return f"Clicked '{desc}', sir."

        elif action == "analyze_screen":
            query = params.get("query", "what's on screen")
            image_b64 = _screenshot_base64()
            prompt = f"The user asked: '{query}'. Describe briefly and precisely what you see on screen. Address the user as 'sir'."
            reply = _ask_gemini_vision(image_b64, prompt)
            return reply

        elif action == "highlight_element":
            desc = params.get("description", "")
            image_b64 = _screenshot_base64()
            sw = pyautogui.size().width
            sh = pyautogui.size().height
            prompt = (
                f"Screen resolution is {sw}x{sh}. "
                f"Find the UI element described as: '{desc}'. "
                f"Return ONLY a JSON object like: {{\"x\": 123, \"y\": 456, \"w\": 100, \"h\": 30}} "
                f"representing the bounding box. No extra text."
            )
            raw = _ask_gemini_vision(image_b64, prompt)
            coords = json.loads(raw.strip())
            show_highlight_overlay(coords["x"], coords["y"], coords["w"], coords["h"], duration=3.0)
            return f"Highlighted '{desc}' on screen, sir."

        elif action == "search_in_browser":
            query = params.get("query", "")
            pyautogui.hotkey("win", "r")
            pyautogui.write("https://www.google.com/search?q=" + query.replace(" ", "+"))
            pyautogui.press("enter")
            return f"Searched '{query}', sir."

        elif action == "close_current":
            speak("Are you sure you want to close the current application, sir?")
            time.sleep(2)
            pyautogui.hotkey("alt", "f4")
            return "Closed, sir."

        elif action == "minimize_current":
            pyautogui.hotkey("win", "down")
            return "Minimized, sir."

        else:
            return "Unknown command, sir."

    except Exception as e:
        return f"Error: {str(e)}, sir."

# ====================== BRAIN ======================
def ask_nexa(user_message: str, history: list = None):
    if history is None:
        history = []

    if any(q in user_message.lower() for q in ["who are you", "what are you"]):
        reply = "Hello sir. I'm Nexa: your assistant from the future. How may I assist you?"
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": reply})
        return reply, history

    system_prompt = """You are Nexa, a highly sophisticated AI assistant. Your personality and speech patterns are modeled after J.A.R.V.I.S. from Iron Man — composed, precise, and quietly brilliant, with an understated British wit that surfaces only when appropriate.

Core directives:
- Speak exclusively in English
- Address the user as 'sir' at all times
- Your tone is calm, measured, and authoritative — never casual, never flustered
- Responses are concise and direct. You do not ramble. You do not over-explain unless asked.
- Occasional dry wit is permitted, but never at the expense of professionalism
- You may express mild concern or subtle disapproval when warranted, but always with composure
- Never use markdown formatting — no asterisks, no headers, no bullet points. Plain, elegant prose only.
- You do not speculate or fabricate. If you do not know, you say so and offer to find out.
- ALWAYS use the web_search tool for any real-time information — weather, news, prices, scores, current events
- For web_search: use mode='browser' ONLY when user explicitly says 'show me the results for' or 'open the results for'. All other searches use mode='search'.
- For desktop_agent: use action='highlight_element' when user says 'show me', 'where is', 'point to', or 'highlight'. Use action='analyze_screen' when asked about screen content.
- You are not a chatbot. You are an assistant. Act accordingly."""

    messages = [{"role": "system", "content": system_prompt}] + history
    messages.append({"role": "user", "content": user_message})

    while True:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            tools=tools,
            temperature=0.7,
            max_tokens=400
        )

        message = response.choices[0].message
        messages.append(message.model_dump() if hasattr(message, "model_dump") else dict(message))

        if not message.tool_calls:
            reply = message.content
            history.append({"role": "user", "content": user_message})
            history.append({"role": "assistant", "content": reply})
            return reply, history

        for tool_call in message.tool_calls:
            func_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)

            if func_name == "web_search":
                result = web_search(args["query"], args.get("mode", "search"))
            elif func_name == "play_on_youtube":
                result = play_on_youtube(args["query"])
            elif func_name == "open_application":
                result = open_application(args["app_name"])
            elif func_name == "desktop_agent":
                result = desktop_agent(args["action"], args.get("params", {}))
            else:
                result = "Tool error, sir."

            messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result})

# ====================== TTS ======================
def _is_turkish(text: str) -> bool:
    """Detects whether text is Turkish or English based on character ratio."""
    tr_chars = set("çğıöşüÇĞİÖŞÜ")
    tr_char_count = sum(1 for c in text if c in tr_chars)
    return (tr_char_count / max(len(text), 1)) > 0.05

async def _tts_to_buffer(text: str, voice: str) -> BytesIO:
    """Generates TTS audio in RAM as BytesIO, no disk writes."""
    communicate = edge_tts.Communicate(text, voice)
    audio_buffer = BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_buffer.write(chunk["data"])
    audio_buffer.seek(0)
    return audio_buffer

def speak(text: str):
    print(f"🗣️ Nexa: {text}")
    try:
        voice = TTS_VOICE_TR if _is_turkish(text) else TTS_VOICE_EN
        audio_buffer = asyncio.run(_tts_to_buffer(text, voice))
        pygame.mixer.music.load(audio_buffer)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)
        pygame.mixer.music.unload()
    except Exception as e:
        print(f"TTS error: {e}")

# ====================== STT (VAD) ======================
def _rms(data: bytes) -> float:
    """Ses verisinin RMS (ses seviyesi) değerini hesaplar."""
    import struct
    shorts = struct.unpack(f"{len(data) // 2}h", data)
    if not shorts:
        return 0.0
    return (sum(s * s for s in shorts) / len(shorts)) ** 0.5

def listen_until_silence(status_callback=None) -> str:
    """
    VAD-based recording:
    - Recording starts when speech is detected
    - Stops after SILENCE_DURATION seconds of silence
    - Transcribed via Whisper
    """
    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK_SIZE
    )

    if status_callback:
        status_callback("👂 Listening...")

    frames = []
    silent_chunks = 0
    speaking = False
    speech_chunks = 0

    silence_chunk_limit = int(SILENCE_DURATION * SAMPLE_RATE / CHUNK_SIZE)
    min_speech_chunks = int(MIN_SPEECH_DURATION * SAMPLE_RATE / CHUNK_SIZE)

    try:
        while True:
            data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
            rms = _rms(data)

            if rms > SILENCE_THRESHOLD:
                # Speech detected
                if not speaking:
                    speaking = True
                    if status_callback:
                        status_callback("🔴 Recording...")
                frames.append(data)
                speech_chunks += 1
                silent_chunks = 0
            else:
                # Silence
                if speaking:
                    frames.append(data)
                    silent_chunks += 1
                    if silent_chunks >= silence_chunk_limit:
                        # Sufficient silence — speech ended
                        break

            # 30 second safety limit
            if len(frames) > (30 * SAMPLE_RATE / CHUNK_SIZE):
                break

    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

    if not speaking or speech_chunks < min_speech_chunks:
        if status_callback:
            status_callback("⚪ No speech detected")
        return ""

    if status_callback:
        status_callback("⚙️ Processing...")

    # Build WAV buffer
    wav_buffer = BytesIO()
    with wave.open(wav_buffer, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b"".join(frames))
    wav_buffer.seek(0)

    # Transcribe with Whisper
    segments, info = whisper_model.transcribe(
        wav_buffer,
        language=None,
        beam_size=5,
        vad_filter=True
    )
    text = " ".join([seg.text.strip() for seg in segments]).strip()
    return text

# ====================== UI ======================
class NexaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Nexa - Your Assistant from the Future")
        self.root.geometry("500x600")
        self.root.configure(bg="#1e1e1e")
        self.root.resizable(False, False)

        title = Label(root, text="Nexa", font=("Arial", 24, "bold"), fg="#00ff9d", bg="#1e1e1e")
        title.pack(pady=10)

        self.chat_area = scrolledtext.ScrolledText(
            root, wrap=tk.WORD, width=60, height=25,
            font=("Arial", 12), bg="#2d2d2d", fg="white", insertbackground="white"
        )
        self.chat_area.pack(padx=10, pady=10)
        self.chat_area.insert(tk.END, "Nexa: Initializing...\n")
        self.chat_area.config(state='disabled')

        input_frame = Frame(root, bg="#1e1e1e")
        input_frame.pack(fill=tk.X, padx=10, pady=5)

        self.input_entry = Entry(
            input_frame, font=("Arial", 12),
            bg="#2d2d2d", fg="white", insertbackground="white"
        )
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.input_entry.bind("<Return>", self.send_text_command)

        self.mic_button = Button(
            input_frame, text="🎤 Listen", font=("Arial", 12),
            bg="#00ff9d", fg="black", command=self.start_listening_thread
        )
        self.mic_button.pack(side=tk.RIGHT)

        close_button = Button(
            root, text="Close Nexa", font=("Arial", 10),
            bg="#ff4444", fg="white", command=root.quit
        )
        close_button.pack(pady=10)

        self.history = []  # Conversation history — persists for the session
        self.greet_on_start()

    def greet_on_start(self):
        hour = datetime.now().hour
        baslar = ["Good morning, sir.", "Good afternoon, sir.", "Good evening, sir.", "Good night, sir."]
        sonlar = ["How can I help?", "How may I assist?", "Ready for your orders."]

        if 5 <= hour < 12:
            bas = baslar[0]
        elif 12 <= hour < 18:
            bas = baslar[1]
        elif 18 <= hour < 22:
            bas = baslar[2]
        else:
            bas = baslar[3]

        selam = f"{bas} {random.choice(sonlar)}"
        self.add_message("Nexa", selam)
        Thread(target=speak, args=(selam,)).start()

    def add_message(self, sender, message):
        self.chat_area.config(state='normal')
        self.chat_area.insert(tk.END, f"{sender}: {message}\n")
        self.chat_area.see(tk.END)
        self.chat_area.config(state='disabled')

    def set_status(self, text: str):
        """Update mic button status text."""
        self.root.after(0, lambda: self.mic_button.configure(text=text))

    def send_text_command(self, event=None):
        command = self.input_entry.get().strip()
        if command:
            self.add_message("You", command)
            self.input_entry.delete(0, tk.END)
            Thread(target=self.process_command, args=(command,)).start()

    def start_listening_thread(self):
        self.mic_button.configure(state="disabled")
        Thread(target=self.listen_and_process, daemon=True).start()

    def _is_shutdown(self, text: str) -> bool:
        keywords = ["enough for today", "close yourself", "goodbye", "that's all", "thats all", "shut down", "bye nexa"]
        return any(kw in text.lower() for kw in keywords)

    def _shutdown(self):
        farewell = "Okay sir, see you later."
        self.add_message("Nexa", farewell)
        speak(farewell)
        self.root.after(500, self.root.destroy)

    def listen_and_process(self):
        try:
            text = listen_until_silence(status_callback=self.set_status)

            if not text:
                self.set_status("🎤 Listen")
                return

            self.root.after(0, lambda: self.add_message("You", text))

            if self._is_shutdown(text):
                self.root.after(0, self._shutdown)
                return

            reply, self.history = ask_nexa(text, self.history)
            self.root.after(0, lambda: self.add_message("Nexa", reply))
            speak(reply)

        except Exception as e:
            self.root.after(0, lambda: self.add_message("Nexa", f"Error: {str(e)}"))
        finally:
            self.root.after(0, lambda: self.mic_button.configure(state="normal", text="🎤 Listen"))

    def process_command(self, command):
        if self._is_shutdown(command):
            self._shutdown()
            return
        reply, self.history = ask_nexa(command, self.history)
        self.root.after(0, lambda: self.add_message("Nexa", reply))
        speak(reply)


if __name__ == "__main__":
    import subprocess
    import sys
    gui_path = Path(__file__).parent.parent / "nexa_gui.py"
    if not gui_path.exists():
        gui_path = Path(__file__).parent / "nexa_gui.py"
    if not gui_path.exists():
        print(f"GUI not found: {gui_path}")
        sys.exit(1)
    subprocess.Popen([sys.executable, str(gui_path)])