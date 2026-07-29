import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
from agent.voice.schemas import SessionStatus, SessionUpdatePayload
from agent.voice.summary import SummaryService


def test_session_update_payload_shape():
    p = SessionUpdatePayload(
        status=SessionStatus.COMPLETED, duration=42, message_id="m1",
        summary="Registered for Pandharpur Wari.", conversation_title="Yatra registration",
        transcript=[{"role": "user", "content": "hi"}, {"role": "assistant", "content": "namaste"}],
    )
    body = p.model_dump(exclude_none=True, mode="json")
    assert body["status"] == "completed" and body["duration"] == 42
    assert body["message_id"] == "m1" and len(body["transcript"]) == 2


def test_summary_formats_both_sides_of_transcript():
    items = [
        {"role": "user", "content": ["I want to register"]},
        {"role": "assistant", "content": "Sure, what's your name?"},
        {"role": "user", "content": ""},          # empty → skipped
    ]
    out = SummaryService._format_transcript(items)
    assert "user: I want to register" in out
    assert "assistant: Sure, what's your name?" in out
    assert out.count("\n") == 1                    # the empty item was skipped


def test_job_metadata_parses_multimodal_fields():
    from voice_agent import JobMetadata
    m = JobMetadata.parse('{"user_id":"u1","conversation_id":"c1","multimodal_session_id":"s1","message_id":"msg1"}')
    assert m.user_id == "u1" and m.multimodal_session_id == "s1" and m.message_id == "msg1"
    assert JobMetadata.parse(None).multimodal_session_id is None   # empty dispatch doesn't crash
