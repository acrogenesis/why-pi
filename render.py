import subprocess
import sys
from multiprocessing import Pool

import cairo

from timeline import DUR
from video import FPS, H, W, render_frame


def stills(times):
    for t in times:
        data = render_frame(round(t * FPS))
        surface = cairo.ImageSurface.create_for_data(bytearray(data), cairo.FORMAT_ARGB32, W, H)
        surface.write_to_png(f"still_{t:05.2f}.png")


def movie():
    frames = int(DUR * FPS)
    ffmpeg = subprocess.Popen(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-i", "pi.wav",
            "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart",
            "why-pi-is-3.14.mp4",
        ],
        stdin=subprocess.PIPE,
    )
    with Pool(28) as pool:
        for i, frame in enumerate(pool.imap(render_frame, range(frames), chunksize=4)):
            ffmpeg.stdin.write(frame)
            if i % 300 == 0:
                print(f"frame {i}/{frames}", flush=True)
    ffmpeg.stdin.close()
    ffmpeg.wait()


if __name__ == "__main__":
    if sys.argv[1:] and sys.argv[1] == "stills":
        stills([float(x) for x in sys.argv[2:]])
    else:
        movie()
