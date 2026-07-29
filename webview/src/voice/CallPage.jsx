import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Room, RoomEvent, Track } from "livekit-client";
import {
  Phone,
  PhoneOff,
  Mic,
  MicOff,
  VideoOff,
  MoreVertical,
  Captions,
  Landmark,
  Sparkles,
} from "lucide-react";
import { useLang } from "../components/AppShell.jsx";
import { strings, tr } from "../strings.js";
import { getVoiceToken, apiGet } from "../lib/api.js";
import { getContext } from "../lib/swiftchat.js";
import { t } from "../lib/i18n.js";
import { createThread, appendMessage } from "../store/threads.js";

// The voice call is recorded into a chat thread so the transcript (and any
// pass issued during the call) is reachable afterwards, exactly like a chat.
const VOICE_CALL_TITLE = { mr: "व्हॉइस कॉल", hi: "वॉइस कॉल", en: "Voice call" };
const PASS_READY = { mr: "🎫 तुमचे यात्रा पास तयार आहेत.", hi: "🎫 आपके यात्रा पास तैयार हैं।", en: "🎫 Your Yatra pass(es) are ready." };
const OPEN_WALLET = { mr: "📲 पास उघडा (वॉलेट)", hi: "📲 पास खोलें (वॉलेट)", en: "📲 Open passes (wallet)" };
const CALL_ENDED_NOTE = { mr: "— कॉल संपला —", hi: "— कॉल समाप्त —", en: "— call ended —" };
const YOU_LABEL = { mr: "तुम्ही", hi: "आप", en: "You" };
const SETU_LABEL = { mr: "सेतू", hi: "सेतू", en: "Setu" };
const CAPTIONS_HINT = { mr: "बोलायला सुरुवात करा…", hi: "बोलना शुरू करें…", en: "Start speaking…" };

// Full-screen voice call surface — replicates the Pravasi Setu Assistant
// call screens: a blue "Calling…" screen while connecting and a light
// "Listening…" screen with a bottom control bar once connected.
// States: connecting | connected | ended | error | unavailable.
export default function CallPage() {
  const { language, yatra } = useLang();
  const navigate = useNavigate();
  const [state, setState] = useState("connecting");
  const [muted, setMuted] = useState(false);
  const [showCaptions, setShowCaptions] = useState(true);
  const [captionLines, setCaptionLines] = useState([]);   // live {id, role, text}
  const captionsEndRef = useRef(null);
  const roomRef = useRef(null);
  const audioContainerRef = useRef(null);
  const startedRef = useRef(false);
  const threadIdRef = useRef(null);        // the chat thread this call is recorded into
  const seenSegRef = useRef(new Set());    // transcription segment ids already saved
  const finalizedRef = useRef(false);
  const baselinePassesRef = useRef(null);  // pass count at call start (to detect a NEW pass)

  const fetchPassCount = useCallback(async () => {
    try {
      const { user_id } = getContext();
      const data = await apiGet(`/api/passes?user_id=${encodeURIComponent(user_id)}`);
      const passes = Array.isArray(data) ? data : data?.passes || [];
      return passes.length;
    } catch (e) {
      return null;
    }
  }, []);

  // Record a batch of transcription segments into the call's thread. The thread
  // is created lazily on the first real segment, so a call with no speech never
  // leaves an empty thread behind. Only FINAL segments are saved (partials
  // update live but aren't persisted).
  const recordSegments = useCallback((segments, participant) => {
    const isUser = !!participant?.isLocal;
    const role = isUser ? "user" : "bot";

    // 1) Live captions: upsert every segment (partial + final) by id so the
    // caption updates as the words come in; keep the last few lines.
    setCaptionLines((prev) => {
      const map = new Map(prev.map((l) => [l.id, l]));
      for (const seg of segments || []) {
        const text = String(seg?.text || "").trim();
        if (!text) continue;
        map.set(seg.id, { id: seg.id, role, text });
      }
      return [...map.values()].slice(-8);
    });

    // 2) Transcript thread: persist FINAL segments only, once each.
    for (const seg of segments || []) {
      if (!seg?.final) continue;
      const text = String(seg.text || "").trim();
      if (!text || seenSegRef.current.has(seg.id)) continue;
      seenSegRef.current.add(seg.id);
      if (!threadIdRef.current) {
        threadIdRef.current = createThread({ title: t(VOICE_CALL_TITLE, language) }).id;
      }
      appendMessage(threadIdRef.current, { role, text });
    }
  }, [language]);

  // After the call, add the wallet link ONLY if a NEW pass was actually issued
  // during THIS call (pass count went up). Ending mid-registration issues no
  // pass, so no link — and a pass from an earlier session never triggers it.
  const finalizeCall = useCallback(async () => {
    if (finalizedRef.current) return;
    finalizedRef.current = true;
    const tid = threadIdRef.current;
    if (!tid) return;
    appendMessage(tid, { role: "bot", text: t(CALL_ENDED_NOTE, language) });
    const before = baselinePassesRef.current;
    const after = await fetchPassCount();
    if (before != null && after != null && after > before) {
      const { user_id } = getContext();
      const url = `${window.location.origin}/yatri/passes?user_id=${encodeURIComponent(user_id)}&lang=${language}`;
      appendMessage(tid, { role: "bot", text: `${t(PASS_READY, language)}\n\n[${t(OPEN_WALLET, language)}](${url})` });
    }
  }, [language, fetchPassCount]);

  const cleanupRoom = useCallback(() => {
    const room = roomRef.current;
    roomRef.current = null;
    if (room) room.disconnect();
  }, []);

  const handleCall = useCallback(async () => {
    setState("connecting");
    setMuted(false);
    // Fresh transcript thread + captions for each call attempt.
    threadIdRef.current = null;
    seenSegRef.current = new Set();
    finalizedRef.current = false;
    baselinePassesRef.current = null;
    setCaptionLines([]);
    try {
      // Pass the caller's SELECTED language + yatra (not the webview default),
      // so the voice AND captions open in the language they chose.
      const { user_id } = getContext();
      const { url, token } = await getVoiceToken({ user_id, yatra, language });

      const room = new Room();
      roomRef.current = room;

      room.on(RoomEvent.TrackSubscribed, (track) => {
        if (track.kind === Track.Kind.Audio) {
          const el = track.attach();
          el.autoplay = true;
          audioContainerRef.current?.appendChild(el);
        }
      });
      // Live transcript → chat thread (both the pilgrim's speech and Setu's).
      room.on(RoomEvent.TranscriptionReceived, (segments, participant) => {
        recordSegments(segments, participant);
      });
      room.on(RoomEvent.Disconnected, () => {
        roomRef.current = null;
        finalizeCall();
        setState("ended");
      });

      await room.connect(url, token);
      await room.localParticipant.setMicrophoneEnabled(true);
      setState("connected");
      // Baseline pass count so we can tell if THIS call issues a new one.
      baselinePassesRef.current = await fetchPassCount();
    } catch (err) {
      if (err?.code === 503) {
        setState("unavailable");
      } else {
        cleanupRoom();
        setState("error");
      }
    }
  }, [cleanupRoom, fetchPassCount, language, yatra]);

  // Auto-start the call on mount — landing here (a tap on the phone icon)
  // IS the "Call" action, so there is no second tap. Also disconnect any
  // live call when navigating away / unmounting.
  useEffect(() => {
    if (!startedRef.current) {
      startedRef.current = true;
      handleCall();
    }
    return () => cleanupRoom();
  }, [handleCall, cleanupRoom]);

  // Keep the captions scrolled to the newest line.
  useEffect(() => {
    captionsEndRef.current?.scrollIntoView({ block: "end" });
  }, [captionLines]);

  const handleHangUp = useCallback(() => {
    finalizeCall();          // save the transcript + wallet link (idempotent)
    cleanupRoom();
    navigate("/");           // land on chat with the voice thread open
  }, [cleanupRoom, navigate, finalizeCall]);

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

  // Assistant avatar — round, with the brand glyph and the yellow "AI" chip.
  const Avatar = ({ chip }) => (
    <div className="relative">
      <div className="w-32 h-32 rounded-full bg-[#E5E7EB] border-4 border-white/70 shadow-card flex items-center justify-center">
        <Landmark size={54} className="text-primary/70" />
      </div>
      <span
        className={`absolute -top-2 -right-1 inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[13px] font-extrabold border-2 border-ai-ring text-ai-ring ${chip}`}
      >
        <Sparkles size={13} /> AI
      </span>
    </div>
  );

  // ---- Connected: "Listening…" screen (light background + control bar) ----
  if (state === "connected") {
    return (
      <div className="fixed inset-0 z-50 bg-lavender-50 flex flex-col items-center justify-center font-sans">
        <button
          type="button"
          onClick={() => setShowCaptions((v) => !v)}
          className={`absolute top-4 right-4 z-10 w-11 h-11 rounded-full shadow-card flex items-center justify-center ${showCaptions ? "bg-primary text-white" : "bg-white text-primary"}`}
          aria-label={t({ mr: "उपशीर्षके", hi: "कैप्शन", en: "Captions" }, language)}
          aria-pressed={showCaptions}
          title="Captions"
        >
          <Captions size={18} />
        </button>

        {/* Live captions — both sides, streaming as they speak (top overlay). */}
        {showCaptions ? (
          <div className="absolute top-0 inset-x-0 h-[42%] px-4 pt-20 pb-3 overflow-y-auto">
            <div className="max-w-2xl mx-auto">
              {captionLines.length === 0 ? (
                <p className="text-center text-[14px] text-muted">{t(CAPTIONS_HINT, language)}</p>
              ) : (
                <div className="space-y-2.5">
                  {captionLines.map((l) => (
                    <div key={l.id} className={l.role === "user" ? "text-right" : "text-left"}>
                      <div className="text-[11px] font-bold uppercase tracking-wide text-muted mb-0.5">
                        {t(l.role === "user" ? YOU_LABEL : SETU_LABEL, language)}
                      </div>
                      <div className={`inline-block max-w-[85%] rounded-2xl px-4 py-2.5 text-[15px] leading-relaxed shadow-card ${l.role === "user" ? "bg-primary text-white rounded-br-md" : "bg-white text-ink rounded-tl-md"}`}>
                        {l.text}
                      </div>
                    </div>
                  ))}
                  <div ref={captionsEndRef} />
                </div>
              )}
            </div>
          </div>
        ) : null}

        <div className="flex flex-col items-center gap-5 -mt-10">
          <Avatar chip="bg-primary" />
          <div className="bg-white rounded-full px-6 py-3.5 shadow-card flex items-center gap-2.5">
            <span className="w-2.5 h-2.5 rounded-full bg-primary animate-pulse" />
            <span className="text-[16px] font-bold text-ink">{tr(strings, "listening", language)}</span>
          </div>
        </div>

        <div className="absolute bottom-6 inset-x-0 px-4 flex items-center justify-center gap-3">
          <div className="w-14 h-14 rounded-full bg-white shadow-card flex items-center justify-center text-primary flex-shrink-0">
            <VideoOff size={22} />
          </div>
          <button
            type="button"
            onClick={handleToggleMute}
            className="flex-1 max-w-md h-14 rounded-full bg-primary text-white flex items-center justify-center shadow-card hover:bg-primary-700 transition"
            aria-label={muted ? tr(strings, "unmute", language) : tr(strings, "mute", language)}
          >
            {muted ? <MicOff size={22} /> : <Mic size={22} />}
          </button>
          <div className="w-14 h-14 rounded-full bg-white shadow-card flex items-center justify-center text-muted flex-shrink-0">
            <MoreVertical size={22} />
          </div>
          <button
            type="button"
            onClick={handleHangUp}
            className="w-14 h-14 rounded-full bg-red-500 text-white flex items-center justify-center shadow-card hover:bg-red-600 transition flex-shrink-0"
            aria-label={tr(strings, "hangUp", language)}
          >
            <PhoneOff size={22} />
          </button>
        </div>

        <div ref={audioContainerRef} style={{ display: "none" }} />
      </div>
    );
  }

  // ---- Ended / error / unavailable: status screen (blue background) ----
  if (state === "ended" || state === "error" || state === "unavailable") {
    const message =
      state === "unavailable"
        ? tr(strings, "voiceUnavailable", language)
        : state === "error"
        ? tr(strings, "callError", language)
        : tr(strings, "callEnded", language);
    return (
      <div className="fixed inset-0 z-50 bg-primary text-white flex flex-col items-center justify-center font-sans px-6">
        <Avatar chip="" />
        <p className="mt-8 text-center text-[16px] text-white/90 max-w-sm leading-relaxed">{message}</p>
        <div className="mt-8 flex flex-col items-center gap-3 w-full max-w-xs">
          {state !== "unavailable" ? (
            <button
              type="button"
              onClick={handleCall}
              className="w-full h-12 rounded-full bg-white text-primary font-extrabold flex items-center justify-center gap-2 hover:bg-white/90 transition"
            >
              <Phone size={18} /> {tr(strings, "callAgain", language)}
            </button>
          ) : null}
          <button
            type="button"
            onClick={() => navigate("/")}
            className="w-full h-12 rounded-full border border-white/50 text-white font-bold flex items-center justify-center hover:bg-white/10 transition"
          >
            {tr(strings, "backToChat", language)}
          </button>
        </div>
        <div ref={audioContainerRef} style={{ display: "none" }} />
      </div>
    );
  }

  // ---- Connecting: "Calling…" screen (blue background + pulsing avatar) ----
  return (
    <div className="fixed inset-0 z-50 bg-primary text-white flex flex-col items-center justify-center font-sans">
      <div className="relative flex items-center justify-center">
        <span className="absolute w-52 h-52 rounded-full bg-white/10 animate-ping" />
        <span className="absolute w-44 h-44 rounded-full bg-white/15" />
        <Avatar chip="" />
      </div>

      <div className="mt-10 text-center px-6">
        <div className="text-[26px] sm:text-[28px] font-extrabold leading-tight">
          <span className="text-white">{tr(strings, "calling", language)} </span>
          <span className="text-ai-ring">{tr(strings, "calleeName", language)}…</span>
        </div>
        <div className="mt-2 text-[17px] text-white/85">{tr(strings, "gettingReady", language)}</div>
      </div>

      <button
        type="button"
        onClick={handleHangUp}
        className="mt-10 w-16 h-16 rounded-full bg-red-500 text-white flex items-center justify-center shadow-card hover:bg-red-600 transition"
        aria-label={tr(strings, "hangUp", language)}
      >
        <PhoneOff size={24} />
      </button>

      <div ref={audioContainerRef} style={{ display: "none" }} />
    </div>
  );
}
