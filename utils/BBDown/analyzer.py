import subprocess
import os

# switch to the script directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))


video_url = "https://www.bilibili.com/video/BV1VUzTB3Ecb"
process=subprocess.Popen(
                ['BBDown', '-info', video_url],
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True
                )
stdout, stderr = process.communicate()
# ignore stderr
output = stdout
lines = output.splitlines()


import re

STREAM_LINE_RE = re.compile(r"^(?P<idx>\d+)\.\s+(?P<rest>.+)$")
BRACKET_RE = re.compile(r"\[(.*?)\]")
URL_RE = re.compile(r"^https?://")

streams = []

i = 0
while i < len(lines) - 1:
    line = lines[i].strip()
    next_line = lines[i + 1].strip()

    m = STREAM_LINE_RE.match(line)
    if m and URL_RE.match(next_line):
        idx = int(m.group("idx"))
        brackets = BRACKET_RE.findall(m.group("rest"))

        streams.append({
            "index": idx,
            "tags": brackets,   # ← 不强行解释
            "url": next_line,
            "raw": line,
        })

        i += 2
        continue

    i += 1

print("Extracted Streams:")
for stream in streams:
    print(f"Index: {stream['index']}, Tags: {stream['tags']}, URL: {stream['url']}")