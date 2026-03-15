import { useState, useRef, useCallback } from "react";
import { uploadImage, streamGenerate, fetchResult, EchoesResult } from "@/lib/echoesApi";

export type EchoesPhase =
  | "idle"
  | "uploading"
  | "generating"
  | "done"
  | "error";

export function useEchoes() {
  const [phase, setPhase] = useState<EchoesPhase>("idle");
  const [streamedText, setStreamedText] = useState("");
  const [result, setResult] = useState<EchoesResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const cancelRef = useRef<(() => void) | null>(null);

  const generate = useCallback(async (file: File) => {
    setPhase("uploading");
    setStreamedText("");
    setResult(null);
    setError(null);

    try {
      const jobId = await uploadImage(file);
      setPhase("generating");

      cancelRef.current = streamGenerate(
        jobId,
        (token) => {
          setStreamedText((prev) => prev + token);
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
  }, []);

  return { phase, streamedText, result, error, generate, reset };
}
