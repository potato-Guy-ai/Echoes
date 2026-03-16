import { EchoesResult } from "@/lib/echoesApi";
import { EchoesPhase } from "@/hooks/useEchoes";

interface IllustrationPanelProps {
  originalImage: string | null;
  result: EchoesResult | null;
  phase: EchoesPhase;
}

export function IllustrationPanel({ originalImage, result, phase }: IllustrationPanelProps) {
  if (!originalImage && !result) return null;

  const isGenerating = phase === "narrating" || phase === "generating";

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      {/* Original photo */}
      {originalImage && (
        <div className="space-y-2">
          <p className="text-xs font-body text-stone-400 uppercase tracking-widest">Your photograph</p>
          <div className="relative overflow-hidden rounded-xl aspect-square">
            <img
              src={originalImage}
              alt="Uploaded photograph"
              className="w-full h-full object-cover"
              style={{ filter: "sepia(0.15) contrast(1.05)" }}
            />
          </div>
        </div>
      )}

      {/* Illustration — skeleton while generating, real image when ready */}
      <div className="space-y-2">
        <p className="text-xs font-body text-stone-400 uppercase tracking-widest">As memory sees it</p>
        <div className="relative overflow-hidden rounded-xl aspect-square bg-stone-100">
          {result?.illustration_url ? (
            <img
              src={result.illustration_url}
              alt="AI-generated illustration"
              className="w-full h-full object-cover animate-fade-in"
            />
          ) : (
            // Skeleton shimmer while generating
            <div className="w-full h-full flex flex-col items-center justify-center gap-3">
              <div
                className="absolute inset-0 bg-gradient-to-r from-stone-100 via-stone-200 to-stone-100"
                style={{
                  backgroundSize: "200% 100%",
                  animation: "shimmer 1.8s ease-in-out infinite",
                }}
              />
              {isGenerating && (
                <div className="relative z-10 flex flex-col items-center gap-2">
                  <svg
                    className="w-6 h-6 animate-spin text-stone-400"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                  </svg>
                  <p className="text-xs font-body text-stone-400">Painting...</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
