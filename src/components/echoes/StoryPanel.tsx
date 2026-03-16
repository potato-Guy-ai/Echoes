import { useEffect, useRef } from "react";
import { EchoesResult } from "@/lib/echoesApi";
import { EchoesPhase } from "@/hooks/useEchoes";
import { Volume2, Mic, Image } from "lucide-react";

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

      {/* Media generating loader — audio + illustration being created in parallel */}
      {phase === "narrating" && (
        <div className="rounded-xl border border-amber-200 bg-amber-50/60 px-4 py-4 space-y-3">
          <div className="flex items-center gap-3">
            <svg
              className="w-4 h-4 shrink-0 animate-spin text-amber-500"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
            </svg>
            <p className="font-body text-sm text-amber-700 font-medium">
              Creating your memory experience...
            </p>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div className="flex items-center gap-2 rounded-lg bg-amber-100/70 px-3 py-2">
              <Mic className="w-3.5 h-3.5 text-amber-600 shrink-0" />
              <div>
                <p className="text-xs font-body text-amber-800 font-medium">Narration</p>
                <p className="text-xs font-body text-amber-600">Recording voice...</p>
              </div>
              <div className="ml-auto flex items-end gap-0.5 h-3">
                {[1,2,3,4].map((i) => (
                  <span
                    key={i}
                    className="w-0.5 rounded-full bg-amber-400"
                    style={{
                      height: `${50 + i * 12}%`,
                      animation: `pulse 0.9s ease-in-out ${i * 0.18}s infinite alternate`,
                    }}
                  />
                ))}
              </div>
            </div>
            <div className="flex items-center gap-2 rounded-lg bg-amber-100/70 px-3 py-2">
              <Image className="w-3.5 h-3.5 text-amber-600 shrink-0" />
              <div>
                <p className="text-xs font-body text-amber-800 font-medium">Illustration</p>
                <p className="text-xs font-body text-amber-600">Painting scene...</p>
              </div>
              <div className="ml-auto">
                <svg className="w-3 h-3 animate-spin text-amber-400" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                </svg>
              </div>
            </div>
          </div>
          <p className="text-xs font-body text-amber-500 text-center">This usually takes 15 - 40 seconds</p>
        </div>
      )}

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
  // If it's clean prose (no JSON markers), return as-is
  if (!raw.includes('{') && !raw.includes('"story"')) return raw;
  // Try to extract story field from partial/complete JSON
  const match = raw.match(/"story"\s*:\s*"((?:[^"\\]|\\.)*)/s);
  if (match) {
    return match[1]
      .replace(/\\n/g, "\n")
      .replace(/\\r/g, "")
      .replace(/\\"/g, '"');
  }
  return raw;
}
