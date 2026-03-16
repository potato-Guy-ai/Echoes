import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { RotateCcw, AlertCircle } from "lucide-react";
import { useEchoes } from "@/hooks/useEchoes";
import { UploadZone } from "@/components/echoes/UploadZone";
import { StoryPanel } from "@/components/echoes/StoryPanel";
import { IllustrationPanel } from "@/components/echoes/IllustrationPanel";

export default function Index() {
  const { phase, streamedText, result, error, mediaStatus, generate, reset } = useEchoes();
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const handleFile = useCallback((file: File) => {
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    generate(file);
  }, [generate]);

  const handleReset = useCallback(() => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
    reset();
  }, [previewUrl, reset]);

  const isActive = phase !== "idle";

  return (
    <div className="min-h-screen bg-[#faf8f5] text-stone-800">
      <div
        className="pointer-events-none fixed inset-0 z-50 opacity-[0.03] animate-grain"
        style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E\")" }}
      />

      <div className="relative z-10 mx-auto max-w-4xl px-6 py-16">
        <motion.header
          initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: "easeOut" }}
          className="mb-14 text-center"
        >
          <h1 className="font-display text-5xl md:text-6xl font-normal tracking-tight text-stone-900 mb-3">Echoes</h1>
          <p className="font-body text-stone-500 text-lg max-w-md mx-auto leading-relaxed">Every photograph holds a story waiting to be told.</p>
        </motion.header>

        <AnimatePresence mode="wait">
          {!isActive ? (
            <motion.div key="upload" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -12 }} transition={{ duration: 0.5 }}>
              <UploadZone onFile={handleFile} />
            </motion.div>
          ) : (
            <motion.div key="result" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.6 }} className="space-y-10">
              {error && (
                <div className="flex items-start gap-3 rounded-xl bg-red-50 border border-red-200 p-4 text-red-700">
                  <AlertCircle className="w-5 h-5 mt-0.5 shrink-0" />
                  <div>
                    <p className="font-body text-sm font-medium">Something went wrong</p>
                    <p className="font-body text-xs text-red-500 mt-0.5">{error}</p>
                  </div>
                </div>
              )}

              <IllustrationPanel originalImage={previewUrl} result={result} phase={phase} mediaStatus={mediaStatus} />

              <div className="bg-white/70 backdrop-blur-sm rounded-2xl border border-stone-200/80 p-8 shadow-sm">
                <StoryPanel phase={phase} streamedText={streamedText} result={result} mediaStatus={mediaStatus} />
              </div>

              {(phase === "done" || phase === "error") && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }} className="flex justify-center">
                  <button
                    onClick={handleReset}
                    className="inline-flex items-center gap-2 px-6 py-3 rounded-full border border-stone-300 text-stone-600 font-body text-sm hover:bg-stone-100 hover:border-stone-400 transition-all duration-200"
                  >
                    <RotateCcw className="w-4 h-4" />
                    Try another photograph
                  </button>
                </motion.div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <style>{`
        @keyframes shimmer { 0% { background-position: -200% 0; } 100% { background-position: 200% 0; } }
      `}</style>
    </div>
  );
}
