import logging
from pathlib import Path

import pandas as pd
import torch

logger = logging.getLogger(__name__)


class ExtractWordsFromAudio:
    language: str = "english"
    overwrite: bool = False

    @staticmethod
    def _get_transcript_from_audio(wav_filename: Path, language: str) -> pd.DataFrame:
        import json
        import os
        import subprocess
        import tempfile

        language_codes = dict(
            english="en", french="fr", spanish="es", dutch="nl", chinese="zh"
        )

        if language not in language_codes:
            raise ValueError(f"Language {language} not supported")

        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"
        batch_size = "16" if device == "cuda" else "1"
        model_name = "large-v3" if device == "cuda" else "small"

        with tempfile.TemporaryDirectory() as output_dir:
            logger.info(
                f"Running whisperx via uvx (device={device}, compute_type={compute_type}, model={model_name})"
            )

            cmd = [
                "uvx",
                "whisperx",
                str(wav_filename),
                "--model",
                model_name,
                "--language",
                language_codes[language],
                "--device",
                device,
                "--compute_type",
                compute_type,
                "--batch_size",
                batch_size,
                "--align_model",
                "WAV2VEC2_ASR_LARGE_LV60K_960H" if language == "english" else "",
                "--output_dir",
                output_dir,
                "--output_format",
                "json",
            ]

            cmd = [c for c in cmd if c]
            env = {k: v for k, v in os.environ.items() if k != "MPLBACKEND"}

            result = subprocess.run(cmd, capture_output=True, text=True, env=env)

            if result.returncode != 0:
                raise RuntimeError(f"whisperx failed:\n{result.stderr}")

            json_path = Path(output_dir) / f"{wav_filename.stem}.json"
            transcript = json.loads(json_path.read_text())

        words = []

        for i, segment in enumerate(transcript["segments"]):
            sentence = segment["text"].replace('"', "")

            for word in segment["words"]:
                if "start" not in word:
                    continue

                word_dict = {
                    "text": word["word"].replace('"', ""),
                    "start": word["start"],
                    "duration": word["end"] - word["start"],
                    "sequence_id": i,
                    "sentence": sentence,
                }
                words.append(word_dict)

        return pd.DataFrame(words)
