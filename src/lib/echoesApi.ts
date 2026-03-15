const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:5000";

export interface EchoesResult {
  story: string;
  scene_description: string;
  mood: string[];
  illustration_url: string;
}

export async function uploadImage(file: File): Promise<string> {
  const formData = new FormData();
  formData.append("image", file);

  const res = await fetch(`${BACKEND_URL}/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) throw new Error("Upload failed");
  const data = await res.json();
  return data.job_id as string;
}

export function streamGenerate(
  jobId: string,
  onToken: (token: string) => void,
  onDone: () => void,
  onError: (err: Error) => void
): () => void {
  let cancelled = false;

  (async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: jobId }),
      });

      if (!res.ok || !res.body) throw new Error("Generate request failed");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        if (cancelled) break;
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const payload = line.slice(6);
          if (payload === "[DONE]") {
            if (!cancelled) onDone();
            return;
          }
          if (!cancelled) onToken(payload);
        }
      }
    } catch (err) {
      if (!cancelled) onError(err instanceof Error ? err : new Error(String(err)));
    }
  })();

  return () => {
    cancelled = true;
  };
}

export async function fetchResult(jobId: string): Promise<EchoesResult> {
  const res = await fetch(`${BACKEND_URL}/result?job_id=${jobId}`);
  if (!res.ok) throw new Error("Failed to fetch result");
  return res.json() as Promise<EchoesResult>;
}
