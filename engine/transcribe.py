from faster_whisper import WhisperModel

def extract_word_timestamps(
    audio_path: str,
    model_size: str = "base",
    language: str | None = "id",
    device: str = "cpu",
    compute_type: str = "int8"
) -> list[dict]:
    model = WhisperModel(model_size, device=device, compute_type=compute_type)
    segments, _ = model.transcribe(
        audio_path,
        language=language,
        word_timestamps=True,
        vad_filter=True
    )

    words_list = []
    for segment in segments:
        if not segment.words:
            continue
        for w in segment.words:
            clean_word = w.word.strip()
            if clean_word:
                words_list.append({
                    "word": clean_word,
                    "start": round(w.start, 3),
                    "end": round(w.end, 3)
                })
    return words_list

def group_words_into_chunks(
    words: list[dict],
    max_words_per_chunk: int = 6,
    max_duration_sec: float = 3.2
) -> list[dict]:
    if not words:
        return []

    chunks = []
    current_group = []

    for item in words:
        if not current_group:
            current_group.append(item)
            continue

        group_start = current_group[0]["start"]
        projected_dur = item["end"] - group_start

        if len(current_group) >= max_words_per_chunk or projected_dur > max_duration_sec:
            chunks.append(_finalize_chunk(current_group))
            current_group = [item]
        else:
            current_group.append(item)

    if current_group:
        chunks.append(_finalize_chunk(current_group))

    for i in range(len(chunks) - 1):
        next_start = chunks[i + 1]["start_sec"]
        chunks[i]["duration_sec"] = round(next_start - chunks[i]["start_sec"], 3)

    return chunks

def _finalize_chunk(group: list[dict]) -> dict:
    chunk_start = group[0]["start"]
    chunk_end = group[-1]["end"]
    normalized_words = [
        {
            "word": w["word"],
            "start": round(w["start"] - chunk_start, 3),
            "end": round(w["end"] - chunk_start, 3)
        }
        for w in group
    ]
    return {
        "start_sec": chunk_start,
        "duration_sec": round(max(0.5, chunk_end - chunk_start), 3),
        "words": normalized_words
    }
