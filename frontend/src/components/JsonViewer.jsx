import { useState } from "react";
import { Copy, Check, ChevronRight, ChevronDown } from "lucide-react";

export default function JsonViewer({ data, title = "JSON Response" }) {
  const [copied, setCopied] = useState(false);
  const [expanded, setExpanded] = useState(true);

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(data, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  return (
    <div className="glass-panel overflow-hidden">
      <div className="flex items-center justify-between p-4 border-b border-ash/30">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-2 text-light hover:text-cyan-glow transition-colors"
        >
          {expanded ? (
            <ChevronDown className="w-4 h-4" />
          ) : (
            <ChevronRight className="w-4 h-4" />
          )}
          <span className="font-semibold font-[Syne]">{title}</span>
        </button>
        <button
          onClick={copyToClipboard}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-cyan-glow/10 hover:bg-cyan-glow/20 text-cyan-glow text-sm transition-colors"
        >
          {copied ? (
            <>
              <Check className="w-4 h-4" />
              Copied!
            </>
          ) : (
            <>
              <Copy className="w-4 h-4" />
              Copy
            </>
          )}
        </button>
      </div>

      {expanded && (
        <div className="p-4 bg-void/50 overflow-x-auto max-h-96 overflow-y-auto">
          <pre className="font-mono text-xs leading-relaxed">
            <JsonSyntaxHighlight data={data} />
          </pre>
        </div>
      )}
    </div>
  );
}

function JsonSyntaxHighlight({ data, indent = 0 }) {
  const spaces = "  ".repeat(indent);

  if (data === null) {
    return <span className="text-slate-400">null</span>;
  }

  if (typeof data === "boolean") {
    return <span className="text-purple-400">{data.toString()}</span>;
  }

  if (typeof data === "number") {
    return <span className="text-amber-400">{data}</span>;
  }

  if (typeof data === "string") {
    return <span className="text-emerald-400">"{data}"</span>;
  }

  if (Array.isArray(data)) {
    if (data.length === 0) return <span>[]</span>;

    return (
      <>
        {"[\n"}
        {data.map((item, i) => (
          <span key={i}>
            {spaces} <JsonSyntaxHighlight data={item} indent={indent + 1} />
            {i < data.length - 1 ? ",\n" : "\n"}
          </span>
        ))}
        {spaces}
        {"]"}
      </>
    );
  }

  if (typeof data === "object") {
    const keys = Object.keys(data);
    if (keys.length === 0) return <span>{"{}"}</span>;

    return (
      <>
        {"{\n"}
        {keys.map((key, i) => (
          <span key={key}>
            {spaces} <span className="text-cyan-400">"{key}"</span>:{" "}
            <JsonSyntaxHighlight data={data[key]} indent={indent + 1} />
            {i < keys.length - 1 ? ",\n" : "\n"}
          </span>
        ))}
        {spaces}
        {"}"}
      </>
    );
  }

  return <span>{String(data)}</span>;
}
