import { useCallback, useState } from "react";
import { Upload, ImageIcon } from "lucide-react";

interface UploadZoneProps {
  onFile: (file: File) => void;
  disabled?: boolean;
}

export function UploadZone({ onFile, disabled }: UploadZoneProps) {
  const [dragging, setDragging] = useState(false);

  const handleFile = useCallback(
    (file: File) => {
      if (!file.type.startsWith("image/")) return;
      onFile(file);
    },
    [onFile]
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const onInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  return (
    <label
      className={[
        "group relative flex flex-col items-center justify-center gap-4",
        "w-full min-h-[280px] rounded-2xl border-2 border-dashed",
        "cursor-pointer transition-all duration-300",
        dragging
          ? "border-amber-400 bg-amber-50/60"
          : "border-stone-300 bg-stone-50/40 hover:border-amber-300 hover:bg-amber-50/30",
        disabled ? "pointer-events-none opacity-50" : "",
      ].join(" ")}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
    >
      <input
        type="file"
        accept="image/*"
        className="sr-only"
        onChange={onInputChange}
        disabled={disabled}
      />
      <div className="flex flex-col items-center gap-3 text-stone-500 group-hover:text-amber-700 transition-colors">
        <div className="rounded-full bg-stone-100 p-4 group-hover:bg-amber-100 transition-colors">
          <ImageIcon className="w-8 h-8" />
        </div>
        <div className="text-center">
          <p className="font-display text-lg text-stone-700">Drop a photograph here</p>
          <p className="text-sm text-stone-400 mt-1">or click to browse your files</p>
        </div>
        <div className="flex items-center gap-2 text-xs text-stone-400">
          <Upload className="w-3 h-3" />
          <span>JPG, PNG, WEBP supported</span>
        </div>
      </div>
    </label>
  );
}
