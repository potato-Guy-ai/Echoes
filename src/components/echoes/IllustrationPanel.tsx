import { EchoesResult } from "@/lib/echoesApi";

interface IllustrationPanelProps {
  originalImage: string | null;
  result: EchoesResult | null;
}

export function IllustrationPanel({ originalImage, result }: IllustrationPanelProps) {
  if (!originalImage && !result) return null;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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

      {result?.illustration_url && (
        <div className="space-y-2">
          <p className="text-xs font-body text-stone-400 uppercase tracking-widest">As memory sees it</p>
          <div className="relative overflow-hidden rounded-xl aspect-square bg-stone-100">
            <img
              src={result.illustration_url}
              alt="AI-generated illustration"
              className="w-full h-full object-cover animate-fade-in"
            />
          </div>
        </div>
      )}
    </div>
  );
}
