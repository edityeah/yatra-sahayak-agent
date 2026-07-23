import { useCallback, useEffect, useRef, useState } from "react";
import { Room, RoomEvent, Track } from "livekit-client";
import { useLang } from "../components/AppShell.jsx";
import { strings, tr } from "../strings.js";
import { Card, ErrorNote, Pill } from "../components/ui.jsx";
import { getVoiceToken } from "../lib/api.js";
import { getContext } from "../lib/swiftchat.js";

// Voice call page — browser "Call" button using the LiveKit JS client.
// States: idle | connecting | connected | ended | error | unavailable.
export default function CallPage() {
  const { language } = useLang();
  const [state, setState] = useState("idle");
  const [muted, setMuted] = useState(false);
  const roomRef = useRef(null);
  const audioContainerRef = useRef(null);

  const cleanupRoom = useCallback(() => {
    const room = roomRef.current;
    roomRef.current = null;
    if (room) room.disconnect();
  }, []);

  useEffect(() => {
    // Disconnect any live call when navigating away / unmounting.
    return () => cleanupRoom();
  }, [cleanupRoom]);

  const handleCall = useCallback(async () => {
    setState("connecting");
    setMuted(false);
    try {
      const { user_id, yatra, language: ctxLanguage } = getContext();
      const { url, token } = await getVoiceToken({ user_id, yatra, language: ctxLanguage });

      const room = new Room();
      roomRef.current = room;

      room.on(RoomEvent.TrackSubscribed, (track) => {
        if (track.kind === Track.Kind.Audio) {
          const el = track.attach();
          el.autoplay = true;
          audioContainerRef.current?.appendChild(el);
        }
      });
      room.on(RoomEvent.Disconnected, () => {
        roomRef.current = null;
        setState("ended");
      });

      await room.connect(url, token);
      await room.localParticipant.setMicrophoneEnabled(true);
      setState("connected");
    } catch (err) {
      if (err?.code === 503) {
        setState("unavailable");
      } else {
        cleanupRoom();
        setState("error");
      }
    }
  }, [cleanupRoom]);

  const handleHangUp = useCallback(() => {
    cleanupRoom();
    setState("ended");
  }, [cleanupRoom]);

  const handleToggleMute = useCallback(async () => {
    const room = roomRef.current;
    if (!room) return;
    const next = !muted;
    try {
      await room.localParticipant.setMicrophoneEnabled(!next);
      setMuted(next);
    } catch (e) {
      // Ignore — mic toggle failures shouldn't crash the call UI.
    }
  }, [muted]);

  const busy = state === "connecting";
  const inCall = state === "connected";

  return (
    <div>
      <h1>{tr(strings, "voice", language)}</h1>

      <Card className="call-card">
        <p className="call-hint">{tr(strings, "callHint", language)}</p>
        <p className="call-mic-note">{tr(strings, "callMicNote", language)}</p>

        <div className="call-stage">
          {!inCall ? (
            <button
              type="button"
              className="call-button"
              onClick={handleCall}
              disabled={busy}
            >
              {busy ? tr(strings, "connecting", language) : tr(strings, "call", language)}
            </button>
          ) : (
            <div className="call-controls">
              <Pill tone="ok">{tr(strings, "connected", language)}</Pill>
              <div className="call-buttons-row">
                <button type="button" className="call-mute-btn" onClick={handleToggleMute}>
                  {muted ? tr(strings, "unmute", language) : tr(strings, "mute", language)}
                </button>
                <button type="button" className="call-hangup-btn" onClick={handleHangUp}>
                  {tr(strings, "hangUp", language)}
                </button>
              </div>
            </div>
          )}
        </div>

        {state === "ended" ? <p className="call-status">{tr(strings, "callEnded", language)}</p> : null}
        {state === "unavailable" ? <ErrorNote>{tr(strings, "voiceUnavailable", language)}</ErrorNote> : null}
        {state === "error" ? <ErrorNote>{tr(strings, "callError", language)}</ErrorNote> : null}

        {/* Subscribed remote audio tracks are attached here (hidden). */}
        <div ref={audioContainerRef} style={{ display: "none" }} />
      </Card>
    </div>
  );
}
