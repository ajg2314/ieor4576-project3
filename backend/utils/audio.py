import asyncio
import os
import re
import uuid
from collections import Counter
from statistics import variance

from google.cloud import speech_v2, storage
from google.cloud.speech_v2 import types as speech_types

from backend.models.schemas import DeliveryMetrics, TranscriptSegment

FILLER_PATTERN = re.compile(
    r"\b(um+|uh+|er+|ah+|like|basically|actually|sort of|kind of|you know)\b",
    re.IGNORECASE,
)
WORD_PATTERN = re.compile(r"[A-Za-z0-9']+")


def _word_count(text: str) -> int:
    return len(WORD_PATTERN.findall(text))


def count_fillers(text: str) -> int:
    return len(FILLER_PATTERN.findall(text))


def _timestamp(seconds: float) -> str:
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"


def _extract_slide_blocks(slide_text: str) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    current_title = ""
    current_lines: list[str] = []

    for line in slide_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[Slide ") and stripped.endswith("]"):
            if current_title and current_lines:
                blocks.append((current_title, " ".join(current_lines)))
            current_title = stripped.strip("[]")
            current_lines = []
        elif stripped:
            current_lines.append(stripped)

    if current_title and current_lines:
        blocks.append((current_title, " ".join(current_lines)))
    return blocks


def align_segments_to_slides(
    segments: list[TranscriptSegment],
    slide_text: str,
) -> list[TranscriptSegment]:
    slide_blocks = _extract_slide_blocks(slide_text)
    if not slide_blocks:
        return segments

    slide_terms = []
    for title, text in slide_blocks:
        terms = {
            word.lower()
            for word in WORD_PATTERN.findall(text)
            if len(word) > 3
        }
        slide_terms.append((title, terms))

    aligned = []
    for segment in segments:
        segment_terms = Counter(
            word.lower()
            for word in WORD_PATTERN.findall(segment.text)
            if len(word) > 3
        )
        best_title: str | None = None
        best_score = 0
        for title, terms in slide_terms:
            score = sum(segment_terms[word] for word in terms)
            if score > best_score:
                best_title = title
                best_score = score
        aligned.append(
            segment.model_copy(update={"aligned_slide": best_title if best_score >= 2 else None})
        )
    return aligned


async def transcribe_audio(file_bytes: bytes, filename: str, content_type: str) -> list[TranscriptSegment]:
    return await asyncio.to_thread(_transcribe_audio_sync, file_bytes, filename, content_type)


def _transcribe_audio_sync(file_bytes: bytes, filename: str, content_type: str) -> list[TranscriptSegment]:
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT")
    if not project_id:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT is required for Google Speech-to-Text transcription.")

    bucket_name = os.getenv("STORYCOACH_AUDIO_BUCKET") or os.getenv("GOOGLE_CLOUD_STORAGE_BUCKET")
    if bucket_name:
        return _transcribe_from_gcs(file_bytes, filename, content_type, project_id, bucket_name)
    return _transcribe_inline(file_bytes, project_id)


def _recognizer_name(project_id: str) -> str:
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "global")
    return f"projects/{project_id}/locations/{location}/recognizers/_"


def _recognition_config() -> speech_types.RecognitionConfig:
    return speech_types.RecognitionConfig(
        auto_decoding_config=speech_types.AutoDetectDecodingConfig(),
        language_codes=[os.getenv("STORYCOACH_TRANSCRIPTION_LANGUAGE", "en-US")],
        model=os.getenv("STORYCOACH_SPEECH_MODEL", "latest_long"),
        features=speech_types.RecognitionFeatures(
            enable_word_time_offsets=True,
            enable_automatic_punctuation=True,
        ),
    )


def _transcribe_inline(file_bytes: bytes, project_id: str) -> list[TranscriptSegment]:
    client = speech_v2.SpeechClient()
    request = speech_types.RecognizeRequest(
        recognizer=_recognizer_name(project_id),
        config=_recognition_config(),
        content=file_bytes,
    )
    response = client.recognize(request=request)
    return _segments_from_recognition_results(response.results)


def _transcribe_from_gcs(
    file_bytes: bytes,
    filename: str,
    content_type: str,
    project_id: str,
    bucket_name: str,
) -> list[TranscriptSegment]:
    gcs_uri = _upload_audio_to_gcs(file_bytes, filename, content_type, bucket_name)

    client = speech_v2.SpeechClient()
    request = speech_types.BatchRecognizeRequest(
        recognizer=_recognizer_name(project_id),
        config=_recognition_config(),
        files=[speech_types.BatchRecognizeFileMetadata(uri=gcs_uri)],
        recognition_output_config=speech_types.RecognitionOutputConfig(
            inline_response_config=speech_types.InlineOutputConfig()
        ),
    )
    operation = client.batch_recognize(request=request)
    response = operation.result(timeout=int(os.getenv("STORYCOACH_SPEECH_TIMEOUT_SECONDS", "900")))

    file_result = response.results.get(gcs_uri)
    if not file_result:
        raise RuntimeError("Speech-to-Text returned no result for the uploaded rehearsal audio.")
    if file_result.error and file_result.error.message:
        raise RuntimeError(f"Speech-to-Text failed: {file_result.error.message}")

    transcript = file_result.inline_result.transcript
    return _segments_from_recognition_results(transcript.results)


def _upload_audio_to_gcs(
    file_bytes: bytes,
    filename: str,
    content_type: str,
    bucket_name: str,
) -> str:
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", filename or "rehearsal_audio")
    object_name = f"rehearsals/{uuid.uuid4()}-{safe_name}"

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_name)
    blob.upload_from_string(file_bytes, content_type=content_type)
    return f"gs://{bucket_name}/{object_name}"


def _duration_seconds(duration) -> float:
    return float(getattr(duration, "seconds", 0)) + float(getattr(duration, "nanos", 0)) / 1_000_000_000


def _segments_from_recognition_results(results) -> list[TranscriptSegment]:
    words = []
    fallback_segments: list[TranscriptSegment] = []
    previous_end = 0.0

    for result in results:
        if not result.alternatives:
            continue
        alternative = result.alternatives[0]
        if alternative.words:
            words.extend(alternative.words)
            continue

        text = alternative.transcript.strip()
        end = _duration_seconds(result.result_end_offset) or previous_end
        start = previous_end
        previous_end = max(previous_end, end)
        if text:
            fallback_segments.append(_make_segment(start, end, text))

    if words:
        return _segments_from_words(words)
    return fallback_segments


def _segments_from_words(words) -> list[TranscriptSegment]:
    segments: list[TranscriptSegment] = []
    bucket_words: list[str] = []
    bucket_start: float | None = None
    bucket_end = 0.0
    window_seconds = int(os.getenv("STORYCOACH_TRANSCRIPT_WINDOW_SECONDS", "30"))

    for word_info in words:
        start = _duration_seconds(word_info.start_offset)
        end = _duration_seconds(word_info.end_offset) or start
        if bucket_start is None:
            bucket_start = start

        if bucket_words and start - bucket_start >= window_seconds:
            segments.append(_make_segment(bucket_start, bucket_end, " ".join(bucket_words)))
            bucket_words = []
            bucket_start = start

        bucket_words.append(word_info.word)
        bucket_end = max(bucket_end, end)

    if bucket_words and bucket_start is not None:
        segments.append(_make_segment(bucket_start, bucket_end, " ".join(bucket_words)))
    return segments


def _make_segment(start: float, end: float, text: str) -> TranscriptSegment:
    duration_minutes = max((end - start) / 60, 1 / 60)
    return TranscriptSegment(
        start_seconds=round(start, 2),
        end_seconds=round(end, 2),
        text=text.strip(),
        wpm=round(_word_count(text) / duration_minutes, 1),
        filler_word_count=count_fillers(text),
    )


def compute_delivery_metrics(segments: list[TranscriptSegment]) -> DeliveryMetrics:
    if not segments:
        return DeliveryMetrics()

    total_duration = max(segment.end_seconds for segment in segments)
    total_words = sum(_word_count(segment.text) for segment in segments)
    duration_minutes = max(total_duration / 60, 1 / 60)
    wpms = [segment.wpm for segment in segments if segment.wpm > 0]
    filler_total = sum(segment.filler_word_count for segment in segments)

    pacing_dropouts = []
    for segment in segments:
        if not segment.wpm:
            continue
        if segment.wpm < 90:
            pacing_dropouts.append(
                f"{_timestamp(segment.start_seconds)}-{_timestamp(segment.end_seconds)}: slow pacing ({segment.wpm:.0f} WPM)"
            )
        elif segment.wpm > 190:
            pacing_dropouts.append(
                f"{_timestamp(segment.start_seconds)}-{_timestamp(segment.end_seconds)}: rushed pacing ({segment.wpm:.0f} WPM)"
            )

    mismatches = [
        f"{_timestamp(segment.start_seconds)}-{_timestamp(segment.end_seconds)}: no strong slide match"
        for segment in segments
        if segment.aligned_slide is None and segment.end_seconds - segment.start_seconds >= 15
    ]

    return DeliveryMetrics(
        total_duration_seconds=round(total_duration, 1),
        average_wpm=round(total_words / duration_minutes, 1),
        wpm_variance=round(variance(wpms), 1) if len(wpms) > 1 else 0.0,
        filler_word_total=filler_total,
        filler_word_density_per_minute=round(filler_total / duration_minutes, 1),
        pacing_dropouts=pacing_dropouts[:8],
        slide_speech_mismatches=mismatches[:8],
    )


def transcript_text(segments: list[TranscriptSegment]) -> str:
    return "\n".join(
        f"[{_timestamp(segment.start_seconds)}-{_timestamp(segment.end_seconds)}"
        f"{f', {segment.aligned_slide}' if segment.aligned_slide else ''}] {segment.text}"
        for segment in segments
    )


def delivery_metrics_block(metrics: DeliveryMetrics, segments: list[TranscriptSegment]) -> str:
    hotspots = [
        f"{_timestamp(segment.start_seconds)}-{_timestamp(segment.end_seconds)}: "
        f"{segment.filler_word_count} fillers"
        for segment in segments
        if segment.filler_word_count >= 3
    ]
    return f"""Total duration: {metrics.total_duration_seconds}s
Average WPM: {metrics.average_wpm}
WPM variance: {metrics.wpm_variance}
Filler total: {metrics.filler_word_total}
Filler density/min: {metrics.filler_word_density_per_minute}
Pacing flags: {metrics.pacing_dropouts}
Slide mismatch flags: {metrics.slide_speech_mismatches}
Filler hotspots: {hotspots[:8]}"""
