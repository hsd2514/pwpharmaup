import { useState, useCallback } from "react";
import { Upload, FileText, X, Dna } from "lucide-react";

export default function FileUpload({ onFileSelect, selectedFile, onClear }) {
  const [isDragOver, setIsDragOver] = useState(false);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragOver(false);

      const files = e.dataTransfer.files;
      if (files.length > 0) {
        const file = files[0];
        if (file.name.endsWith(".vcf") || file.type === "text/plain") {
          onFileSelect(file);
        }
      }
    },
    [onFileSelect],
  );

  const handleFileInput = useCallback(
    (e) => {
      const file = e.target.files?.[0];
      if (file) {
        onFileSelect(file);
      }
    },
    [onFileSelect],
  );

  if (selectedFile) {
    return (
      <div className="glass-panel p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-cyan-glow/10 flex items-center justify-center">
              <FileText className="w-6 h-6 text-cyan-glow" />
            </div>
            <div>
              <p className="font-semibold text-light">{selectedFile.name}</p>
              <p className="text-sm text-mist">
                {(selectedFile.size / 1024).toFixed(1)} KB
              </p>
            </div>
          </div>
          <button
            onClick={onClear}
            className="p-2 rounded-lg hover:bg-ash/50 transition-colors"
          >
            <X className="w-5 h-5 text-mist hover:text-danger" />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`upload-zone p-8 text-center cursor-pointer ${isDragOver ? "drag-over" : ""}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={() => document.getElementById("vcf-input").click()}
    >
      <input
        id="vcf-input"
        type="file"
        accept=".vcf"
        onChange={handleFileInput}
        className="hidden"
      />

      <div className="relative mb-6">
        <div className="w-20 h-20 mx-auto rounded-2xl bg-gradient-to-br from-cyan-glow/20 to-cyan-dim/10 flex items-center justify-center">
          <Dna className="w-10 h-10 text-cyan-glow" />
        </div>
        <div className="absolute -top-1 -right-1 w-8 h-8 rounded-full bg-cyan-glow/20 flex items-center justify-center">
          <Upload className="w-4 h-4 text-cyan-glow" />
        </div>
      </div>

      <h3 className="text-lg font-semibold text-light mb-2 font-[Syne]">
        Upload VCF File
      </h3>
      <p className="text-mist text-sm mb-4">
        Drag & drop your VCF file or click to browse
      </p>
      <p className="text-xs text-ash">Supports VCF format • Max 5MB</p>
    </div>
  );
}
