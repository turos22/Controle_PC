🖐️ Gesture control · [Português](README.md)

Control your computer with hand gestures in real time, using Python, OpenCV and MediaPipe.
It runs on **Linux, Windows and macOS**; only Linux (KDE Plasma on Wayland) has been verified end to end.

> [!NOTE]
> **Inspiration:** this project started from [cv-controle-do-pc](https://github.com/SeraphZz/cv-controle-do-pc),
> by [Augusto Ferraz (@SeraphZz)](https://github.com/SeraphZz). The original is a single script (`main.py`,
> using PyAutoGUI) that moves the cursor, scrolls and changes the volume with gestures, plus voice dictation.
> Starting from it, I rewrote the control: a gesture state machine calibrated with real recordings,
> `uinput` input on Wayland, Windows, macOS and GNOME backends, per-user profile and calibration,
> and tests. Augusto's initial commits remain in this repository's history.

| System | Mouse and keyboard | Window actions | Status |
|---|---|---|---|
| Linux, KDE Plasma (Wayland or X11) | `uinput` | KWin shortcuts over D-Bus | **verified** |
| Linux, GNOME | `uinput` | default keyboard shortcuts | code and tests; unproven |
| Linux, others | `uinput` | mouse, clicks, scrolling and zoom only | partial |
| Windows 10/11 | `SendInput` | Windows shortcuts | code and tests; unproven on real Windows |
| macOS | Quartz (pyobjc) | macOS shortcuts | code and tests with a fake Quartz; unproven |

## Gestures

All of them work with either hand. The program window shows the full legend and lights up the
recognized gesture as it happens.

| Gesture | Action |
|---|---|
| Index finger extended (relative, with acceleration) | move the cursor |
| Pointing, thumb quickly touches and releases the index finger (twice = double) | left click |
| Pointing, thumb quickly touches and releases the middle finger | right click |
| Closed pinch, held still for a moment, then move | hold and drag (nothing else acts meanwhile) |
| Two fingers extended, moving the hand away from where the pose formed | joystick scroll (4 directions) |
| Closed fist → L with the thumb wide open | maximize the window |
| Open hand → claw → open | overview |
| Open hand sweeping quickly sideways (stop before the next one) | desktop to the left / right |
| Three fingers (index, middle, ring) + slide sideways | Alt+Tab (changing the pose chooses) |
| Thumb down held ~0.8 s | close the window |
| Two pinches at the same time, moving apart or together | zoom (Ctrl + wheel) |

Per-gesture test script: [docs/guia-de-testes.md](docs/guia-de-testes.md) (Portuguese).
Windows verification: [docs/verificacao-windows.md](docs/verificacao-windows.md) (Portuguese).

## Installation

You need Python 3.10 or newer (tested on 3.13) and a webcam. If `pip` cannot find a `mediapipe`
build for your Python, use Python 3.12.

### Linux

```bash
python -m venv .venv
.venv/bin/pip install .
```

The program creates a virtual mouse and keyboard through `/dev/uinput`. Check access with
`test -w /dev/uinput && echo ok`. Without it, the program opens in demo mode. To allow it:

```bash
echo 'KERNEL=="uinput", GROUP="input", MODE="0660", OPTIONS+="static_node=uinput"' | sudo tee /etc/udev/rules.d/99-uinput.rules
sudo usermod -aG input $USER   # then log out and back in
```

### Windows

```powershell
py -m venv .venv
.venv\Scripts\pip install .
.venv\Scripts\controle-por-gestos
```

- Allow camera access in Settings → Privacy → Camera.
- Windows does not let a regular program control windows of programs running as administrator.

### macOS

```bash
python3 -m venv .venv
.venv/bin/pip install .
.venv/bin/controle-por-gestos
```

- Allow **Camera** and **Accessibility** for the app you run the command from (Terminal, iTerm…) in
  System Settings → Privacy & Security. Without Accessibility the program warns you and nothing acts.
- On a Mac, "switch windows" is Command+Tab (switches **applications**), "maximize" makes the window
  full screen, and zoom uses Command + wheel.

For development: `pip install -e ".[dev]"`. `requirements.txt` holds the exact versions the project was
tested with.

## Usage

```bash
.venv/bin/controle-por-gestos      # or: .venv/bin/python main.py / python -m controle
```

- `--demonstracao`: recognizes and shows gestures without acting on the system.
- `--camera N`: pick the camera (0 is the first).
- `Esc` pauses (only pauses, never resumes); `P` pauses and resumes. Pausing releases any pressed button or
  key. `Ctrl+Q` quits.
- **Calibration**: on first launch the program offers to calibrate the gestures to your hand (about 40
  seconds, seven poses). You can redo it with the "Calibrate my gestures" button. If the defaults already
  suit you, nothing changes.
- Left menu: calibrate, record a session, digital zoom, mirror the preview, cursor mode and speed,
  smoothing, scroll speed and direction, enable or disable each gesture. Your settings are saved.
- Language: Portuguese or English, following the system (or `"idioma": "pt" | "en"` in the profile).
- The profile (`perfil.json`) lives in `~/.config/controle-por-gestos` (Linux), `%APPDATA%\controle-por-gestos`
  (Windows) or `~/Library/Application Support/controle-por-gestos` (macOS).
- Session recordings keep only the hand landmarks, never images: in `gravacoes/` inside the repository, or in
  the profile folder when installed.
- Output diagnostics (moves the pointer through the corners of the screens and opens/closes the overview,
  without clicking): `python -m controle.diagnostico`.

The camera is opened at 1280x720, 30 fps.

## Tests

```bash
.venv/bin/pytest
```

The tests run on any system: the Windows and macOS backends are tested with stand-ins.

## License

[MIT](LICENSE). The model `controle/dados/hand_landmarker.task` comes from MediaPipe (Google) and follows the MediaPipe license.

Python • OpenCV • MediaPipe • PySide6 • Computer Vision
