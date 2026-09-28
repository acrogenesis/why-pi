# Why π is 3.14

A 40-second motion graphics video: [why-pi-is-3.14.mp4](why-pi-is-3.14.mp4). The picture is drawn with cairo, the sound is synthesized with numpy, and ffmpeg combines them. The melody plays the digits of π.

Prompt:

> make a dynamic ~40 second motion graphics video with sound that shows why PI is 3.14

## Render

```sh
uv run --with pycairo --with numpy --with scipy python audio.py
uv run --with pycairo --with numpy --with scipy python render.py
```
