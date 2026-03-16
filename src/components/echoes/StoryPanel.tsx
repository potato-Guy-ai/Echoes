import { useEffect, useRef } from "react";
import { EchoesResult } from "@/lib/echoesApi";
import { EchoesPhase, MediaStatus } from "@/hooks/useEchoes";
import { Volume2, Mic, ImageIcon, CheckCircle2, XCircle, RefreshCw } from "lucide-react";

interface StoryPanelProps {
  phase: EchoesPhase;
  streamedText: string;
  result: EchoesResult | null;
  mediaStatus: MediaStatus;
}

function Spinner({ className = "" }: { className?: string }) {
  return (
    <svg className={`animate-spin ${className}`} fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
    </svg>
  );
}

function MediaRow({
  icon: Icon,
  label,
  state,
  retry,
  errorMsg,
}: {
  icon: React.ElementType;
  label: string;
  state: "pending" | "retrying" | "ok" | "failed";
  retry: number;
  errorMsg: string | null;
}) {
  return (
    <div className="flex items-center gap-2 rounded-lg bg-amber-100/70 px-3 py-2">
      <Icon className="w-3.5 h-3.5 text-amber-600 shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-xs font-body text-amber-800 font-medium">{label}</p>
        {state === "pending" && <p className="text-xs font-body text-amber-500">Generating...</p>}
        {state === "retrying" && <p className="text-xs font-body text-amber-600">Retrying... (attempt {retry + 1}/3)</p>}
        {state === "ok" && <p className="text-xs font-body text-green-600">Ready!</p>}
        {state === "failed" && <p className="text-xs font-body text-red-500 truncate" title={errorMsg || ""}>{errorMsg || "Failed"}</p>}
      </div>
      <div className="shrink-0">
        {(state === "pending" || state === "retrying") && <Spinner className="w-3 h-3 text-amber-400" />}
        {state === "retrying" && <RefreshCw className="w-3 h-3 text-amber-500 ml-1" />}
        {state === "ok" && <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />}
        {state === "failed" && <XCircle className="w-3.5 h-3.5 text-red-400" />}
      </div>
    </div>
  );
}

export function StoryPanel({ phase, streamedText, result, mediaStatus }: StoryPanelProps) {
  const endRef = useRef<HTMLDivElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [streamedText]);

  useEffect(() => {
    if (result?.audio_url && audioRef.current) {
      audioRef.current.load();
      audioRef.current.play().catch(() => {});
    }
  }, [result?.audio_url]);

  if (phase === "idle") return null;

  if (phase === "uploading") {
    return (
      <div className="flex items-center justify-center py-12 text-stone-400 animate-pulse">
        <p className="font-body text-sm tracking-wide">Reading your photograph...</p>
      </div>
    );
  }

  const displayText = result?.story || streamedText;
  const story = extractStory(displayText);

  return (
    <div className="space-y-6">
      {/* Mood badges */}
      {result?.mood && result.mood.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {result.mood.map((m) => (
            <span key={m} className="px-3 py-1 text-xs rounded-full bg-amber-100 text-amber-800 font-body tracking-wide capitalize">
              {m}
            </span>
          ))}
        </div>
      )}

      {/* Story text */}
      <div className="prose prose-stone prose-sm max-w-none">
        <p className="font-body text-stone-700 leading-relaxed whitespace-pre-wrap">
          {story}
          {phase === "generating" && (
            <span className="inline-block w-1.5 h-4 bg-amber-500 ml-0.5 animate-pulse align-middle" />
          )}
        </p>
      </div>

      {/* Media generation status panel */}
      {phase === "narrating" && (
        <div className="rounded-xl border border-amber-200 bg-amber-50/60 px-4 py-4 space-y-3">
          <div className="flex items-center gap-2">
            <Spinner className="w-4 h-4 text-amber-500" />
            <p className="font-body text-sm text-amber-700 font-medium">Creating your memory experience...</p>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <MediaRow
              icon={Mic}
              label="Narration"
              state={mediaStatus.audioState}
              retry={mediaStatus.audioRetry}
              errorMsg={mediaStatus.audioError}
            />
            <MediaRow
              icon={ImageIcon}
              label="Illustration"
              state={mediaStatus.imgState}
              retry={mediaStatus.imgRetry}
              errorMsg={mediaStatus.imgError}
            />
          </div>
          <p className="text-xs font-body text-amber-400 text-center">Usually takes 15–40 seconds</p>
        </div>
      )}

      {/* Audio player — shown once ready */}
      {result?.audio_url && (
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2 text-xs font-body text-stone-400 uppercase tracking-widest">
            <Volume2 className="w-3.5 h-3.5" />
            <span>Narration</span>
            <CheckCircle2 className="w-3 h-3 text-green-500" />
          </div>
          <audio ref={audioRef} controls className="w-full h-10 rounded-lg accent-amber-600" style={{ colorScheme: "light" }}>
            <source src={result.audio_url} type="audio/mpeg" />
          </audio>
        </div>
      )}

      {/* Audio failed notice */}
      {phase === "done" && !result?.audio_url && mediaStatus.audioState === "failed" && (
        <div className="flex items-center gap-2 text-xs font-body text-red-400 border border-red-200 rounded-lg px-3 py-2">
          <XCircle className="w-3.5 h-3.5 shrink-0" />
          <span>Narration unavailable — {mediaStatus.audioError || "generation failed after 3 attempts"}</span>
        </div>
      )}

      {/* Scene description */}
      {result?.scene_description && (
        <div className="border-l-2 border-amber-200 pl-4">
          <p className="text-xs font-body text-stone-400 uppercase tracking-widest mb-1">Visual</p>
          <p className="text-sm font-body text-stone-500 italic leading-relaxed">{result.scene_description}</p>
        </div>
      )}

      <div ref={endRef} />
    </div>
  );
}

function extractStory(raw: string): string {
  if (!raw.includes('{') && !raw.includes('"story"')) return raw;
  const match = raw.match(/"story"\s*:\s*"((?:[^"\\]|\\.)*)/s);
  if (match) return match[1].replace(/\\n/g, "\n").replace(/\\r/g, "").replace(/\\"/g, '"');
  return raw;
}
