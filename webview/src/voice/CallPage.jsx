import { useCallback, useEffect, useRef, useState } from "react";
import { Room, RoomEvent, Track } from "livekit-client";
import { Phone, PhoneOff, Mic, MicOff } from "lucide-react";
import { useLang } from "../components/AppShell.jsx";
import { strings, tr } from "../strings.js";
import PageShell from "../components/PageShell.jsx";
import { getVoiceToken } from "../lib/api.js";
import { getContext } from "../lib/swiftchat.js";

// Voice call page — browser "Call" button using the LiveKit JS client.
// States: idle | connecting | connected | ended | error | unavailable.
export default function CallPage() {
  const { language } = useLang();
  const [state, setState] = useState("connecting");
  const [muted, setMuted] = useState(false);
  const roomRef = useRef(null);
  const audioContainerRef = useRef(null);
  const startedRef = useRef(false);

  const cleanupRoom = useCallback(() => {
    const room = roomRef.current;
    roomRef.current = null;
    if (room) room.disconnect();
  }, []);

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

  // Auto-start the call as soon as the page mounts — landing here (a tap
  // on the header phone icon) IS the "Call" action, so no second tap.
  // Disconnect any live call when navigating away / unmounting.
  useEffect(() => {
    if (!startedRef.current) {
      startedRef.current = true;
      handleCall();
    }
    return () => cleanupRoom();
  }, [handleCall, cleanupRoom]);

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
    <PageShell title={tr(strings, "voice", language)}>
      <div className="rounded-2xl border border-bdr bg-surface shadow-card p-6 flex flex-col items-center text-center gap-2">
        <p className="text-[13.5px] text-ink font-semibold">{tr(strings, "callHint", language)}</p>
        <p className="text-[12.5px] text-muted">{tr(strings, "callMicNote", language)}</p>

        <div className="mt-4 flex flex-col items-center gap-4 w-full">
          {inCall ? (
            <div className="flex flex-col items-center gap-4 w-full">
              <span className="inline-flex items-center px-3 py-1 rounded-full text-[12px] font-bold bg-green-50 text-green-700 border border-green-200">
                {tr(strings, "connected", language)}
              </span>
              <div className="flex items-center gap-4">
                <button
                  type="button"
                  onClick={handleToggleMute}
                  className="w-12 h-12 rounded-full border border-bdr bg-surface-2 text-ink flex items-center justify-center hover:border-primary transition"
                  aria-label={muted ? tr(strings, "unmute", language) : tr(strings, "mute", language)}
                >
                  {muted ? <MicOff size={18} /> : <Mic size={18} />}
                </button>
                <button
                  type="button"
                  onClick={handleHangUp}
                  className="w-14 h-14 rounded-full bg-red-600 text-white flex items-center justify-center hover:bg-red-700 transition"
                  aria-label={tr(strings, "hangUp", language)}
                >
                  <PhoneOff size={22} />
                </button>
              </div>
            </div>
          ) : busy ? (
            <div className="flex flex-col items-center gap-4">
              <div className="relative flex items-center justify-center">
                <span className="absolute w-16 h-16 rounded-full bg-primary/30 animate-ping" />
                <span className="w-16 h-16 rounded-full bg-primary text-white flex items-center justify-center shadow-card">
                  <Phone size={26} />
                </span>
              </div>
              <button
                type="button"
                onClick={handleHangUp}
                className="w-14 h-14 rounded-full bg-red-600 text-white flex items-center justify-center hover:bg-red-700 transition"
                aria-label={tr(strings, "hangUp", language)}
              >
                <PhoneOff size={22} />
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={handleCall}
              className="w-16 h-16 rounded-full bg-primary text-white flex items-center justify-center shadow-card transition hover:bg-primary-700"
              aria-label={tr(strings, "voice", language)}
            >
              <Phone size={26} />
            </button>
          )}

          {busy ? <p className="text-[13px] text-muted">{tr(strings, "connecting", language)}</p> : null}
        </div>

        {state === "ended" ? (
          <p className="mt-3 text-[13px] text-muted">{tr(strings, "callEnded", language)}</p>
        ) : null}
        {state === "unavailable" ? (
          <div className="mt-3 w-full rounded-2xl border border-red-200 bg-red-50 text-red-700 text-[13.5px] px-4 py-3">
            {tr(strings, "voiceUnavailable", language)}
          </div>
        ) : null}
        {state === "error" ? (
          <div className="mt-3 w-full rounded-2xl border border-red-200 bg-red-50 text-red-700 text-[13.5px] px-4 py-3">
            {tr(strings, "callError", language)}
          </div>
        ) : null}

        {/* Subscribed remote audio tracks are attached here (hidden). */}
        <div ref={audioContainerRef} style={{ display: "none" }} />
      </div>
    </PageShell>
  );
}
