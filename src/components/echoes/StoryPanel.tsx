import { useEffect, useRef } from "react";
import { EchoesResult } from "@/lib/echoesApi";
import { EchoesPhase } from "@/hooks/useEchoes";
import { Volume2 } from "lucide-react";

interface StoryPanelProps {
  phase: EchoesPhase;
  streamedText: string;
  result: EchoesResult | null;
}

export function StoryPanel({ phase, streamedText, result }: StoryPanelProps) {
  const endRef = useRef<HTMLDivElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [streamedText]);

  // Auto-play narration when audio becomes available
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
        <p className="font-body text-sm tracking-wide">Reading your photograph…</p>
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
            <span
              key={m}
              className="px-3 py-1 text-xs rounded-full bg-amber-100 text-amber-800 font-body tracking-wide capitalize"
            >
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

      {/* Audio player */}
      {result?.audio_url && (
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2 text-xs font-body text-stone-400 uppercase tracking-widest">
            <Volume2 className="w-3.5 h-3.5" />
            <span>Narration</span>
          </div>
          <audio
            ref={audioRef}
            controls
            className="w-full h-10 rounded-lg accent-amber-600"
            style={{ colorScheme: "light" }}
          >
            <source src={result.audio_url} type="audio/mpeg" />
          </audio>
        </div>
      )}

      {/* Scene description */}
      {result?.scene_description && (
        <div className="border-l-2 border-amber-200 pl-4">
          <p className="text-xs font-body text-stone-400 uppercase tracking-widest mb-1">Visual</p>
          <p className="text-sm font-body text-stone-500 italic leading-relaxed">
            {result.scene_description}
          </p>
        </div>
      )}

      <div ref={endRef} />
    </div>
  );
}

function extractStory(raw: string): string {
  if (!raw.includes('{') && !raw.includes('"story"')) return raw;
  const match = raw.match(/"story"\s*:\s*"((?:[^"\\]|\\.)*)/s);
  if (match) {
    return match[1].replace(/\\n/g, "\n").replace(/\\r/g, "").replace(/\\"/g, '"');
  }
  return raw;
}
