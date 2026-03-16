import { useState, useRef, useCallback } from "react";
import { uploadImage, streamGenerate, fetchResult, EchoesResult } from "@/lib/echoesApi";

export type EchoesPhase = "idle" | "uploading" | "generating" | "narrating" | "done" | "error";

export interface MediaStatus {
  audioState: "pending" | "retrying" | "ok" | "failed";
  audioError: string | null;
  audioRetry: number;
  imgState: "pending" | "retrying" | "ok" | "failed";
  imgError: string | null;
  imgRetry: number;
}

const defaultMedia: MediaStatus = {
  audioState: "pending", audioError: null, audioRetry: 0,
  imgState: "pending", imgError: null, imgRetry: 0,
};

export function useEchoes() {
  const [phase, setPhase] = useState<EchoesPhase>("idle");
  const [streamedText, setStreamedText] = useState("");
  const [result, setResult] = useState<EchoesResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mediaStatus, setMediaStatus] = useState<MediaStatus>(defaultMedia);
  const cancelRef = useRef<(() => void) | null>(null);

  const generate = useCallback(async (file: File) => {
    setPhase("uploading");
    setStreamedText("");
    setResult(null);
    setError(null);
    setMediaStatus(defaultMedia);

    try {
      const jobId = await uploadImage(file);
      setPhase("generating");

      cancelRef.current = streamGenerate(
        jobId,
        (token) => {
          if (token.includes("[MEDIA_GENERATING]")) {
            setPhase("narrating");
            return;
          }
          if (token.includes("[AUDIO_RETRY:")) {
            const n = parseInt(token.match(/\d+/)?.[0] || "1");
            setMediaStatus(p => ({ ...p, audioState: "retrying", audioRetry: n }));
            return;
          }
          if (token.includes("[IMG_RETRY:")) {
            const n = parseInt(token.match(/\d+/)?.[0] || "1");
            setMediaStatus(p => ({ ...p, imgState: "retrying", imgRetry: n }));
            return;
          }
          if (token.includes("[AUDIO_OK]")) {
            setMediaStatus(p => ({ ...p, audioState: "ok" }));
            return;
          }
          if (token.includes("[IMG_OK]")) {
            setMediaStatus(p => ({ ...p, imgState: "ok" }));
            return;
          }
          if (token.includes("[AUDIO_FAILED:")) {
            const msg = token.match(/\[AUDIO_FAILED:(.*)\]/)?.[1] || "Failed";
            setMediaStatus(p => ({ ...p, audioState: "failed", audioError: msg }));
            return;
          }
          if (token.includes("[IMG_FAILED:")) {
            const msg = token.match(/\[IMG_FAILED:(.*)\]/)?.[1] || "Failed";
            setMediaStatus(p => ({ ...p, imgState: "failed", imgError: msg }));
            return;
          }
          if (token.includes("[ERROR:text:")) return; // swallow error tokens from text phase
          setStreamedText(prev => prev + token);
        },
        async () => {
          try {
            const res = await fetchResult(jobId);
            setResult(res);
            setPhase("done");
          } catch (e) {
            setError("Failed to load result.");
            setPhase("error");
          }
        },
        (err) => {
          setError(err.message);
          setPhase("error");
        }
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
      setPhase("error");
    }
  }, []);

  const reset = useCallback(() => {
    if (cancelRef.current) cancelRef.current();
    setPhase("idle");
    setStreamedText("");
    setResult(null);
    setError(null);
    setMediaStatus(defaultMedia);
  }, []);

  return { phase, streamedText, result, error, mediaStatus, generate, reset };
}
