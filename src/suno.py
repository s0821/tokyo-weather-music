import os
import random
import subprocess
import tempfile

DEFAULT_OUTPUT = "/tmp/suno_output.mp3"
SOUNDFONT_URL = "https://github.com/musescore/MuseScore/raw/master/share/sound/FluidR3Mono_GM.sf3"
SOUNDFONT_PATH = "/tmp/soundfont.sf3"

# 天気・季節に対応するスケールとテンポ
SCALE_MAP = {
    "clear":  [0, 2, 4, 7, 9],        # ペンタトニック（明るい）
    "rain":   [0, 2, 3, 5, 7, 8, 10], # ナチュラルマイナー（しっとり）
    "cloud":  [0, 2, 3, 5, 7, 9, 10], # ドリアン（落ち着き）
    "snow":   [0, 2, 4, 5, 7, 9, 11], # メジャー（透明感）
    "default":[0, 2, 4, 7, 9],
}

TEMPO_MAP = {
    "春": 76, "夏": 88, "秋": 70, "冬": 60,
}

PROGRAM_MAP = {
    "春": 0,   # アコースティックピアノ
    "夏": 25,  # アコースティックギター
    "秋": 0,   # ピアノ
    "冬": 52,  # 合唱（クワイア）
}


def _get_scale(weather_label):
    label = weather_label.lower()
    for key in SCALE_MAP:
        if key in label:
            return SCALE_MAP[key]
    return SCALE_MAP["default"]


def _generate_midi(prompt_data, duration_sec=180):
    try:
        from midiutil import MIDIFile
    except ImportError:
        subprocess.run(["pip", "install", "midiutil", "-q"], check=True)
        from midiutil import MIDIFile

    season = prompt_data.get("season", "春")
    weather = prompt_data.get("weather_label", "晴れ")
    tempo = TEMPO_MAP.get(season, 72)
    scale = _get_scale(weather)
    program = PROGRAM_MAP.get(season, 0)

    midi = MIDIFile(2)
    # トラック0: メロディ
    midi.addTempo(0, 0, tempo)
    midi.addProgramChange(0, 0, 0, program)
    # トラック1: 伴奏
    midi.addTempo(1, 0, tempo)
    midi.addProgramChange(1, 1, 0, 48)  # ストリングス

    beats_per_sec = tempo / 60.0
    total_beats = int(duration_sec * beats_per_sec)
    base_note = 60  # C4

    random.seed(hash(weather + season))

    time = 0
    while time < total_beats:
        # メロディ音符
        interval = random.choice(scale)
        octave = random.choice([0, 0, 12, -12])
        note = base_note + interval + octave
        note = max(48, min(84, note))
        dur = random.choice([1, 1, 2, 0.5, 0.5])
        vel = random.randint(55, 80)
        midi.addNote(0, 0, note, time, dur, vel)

        # 伴奏コード（4拍ごと）
        if int(time) % 4 == 0:
            chord_root = base_note + random.choice([0, 5, 7])
            for interval in [0, 4, 7]:
                midi.addNote(1, 1, chord_root - 12 + interval, time, 4, 45)

        time += dur

    tmp = tempfile.mktemp(suffix=".mid")
    with open(tmp, "wb") as f:
        midi.writeFile(f)
    return tmp


def _download_soundfont():
    if os.path.exists(SOUNDFONT_PATH):
        return SOUNDFONT_PATH
    print("[suno] サウンドフォントをダウンロード中...")
    import urllib.request
    urllib.request.urlretrieve(SOUNDFONT_URL, SOUNDFONT_PATH)
    return SOUNDFONT_PATH


def _midi_to_mp3(midi_path, output_path):
    sf = _download_soundfont()
    wav_path = tempfile.mktemp(suffix=".wav")
    subprocess.run(
        ["fluidsynth", "-ni", sf, midi_path, "-F", wav_path, "-r", "44100"],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        ["ffmpeg", "-y", "-i", wav_path, "-codec:a", "libmp3lame", "-qscale:a", "2", output_path],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return output_path


def generate_music(suno_prompt, output_path=DEFAULT_OUTPUT, prompt_data=None, max_retries=3):
    for attempt in range(max_retries):
        try:
            midi_path = _generate_midi(prompt_data or {}, duration_sec=180)
            _midi_to_mp3(midi_path, output_path)
            print("[suno] 音楽生成完了: {}".format(output_path))
            return output_path
        except Exception as e:
            print("[suno] 試行 {} 失敗: {}".format(attempt + 1, e))

    raise RuntimeError("音楽生成失敗（{}回試行）".format(max_retries))
