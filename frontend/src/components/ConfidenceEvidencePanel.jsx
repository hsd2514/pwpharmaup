import { ShieldCheck, FileSearch, Microscope } from "lucide-react";

const LABELS = {
  evidence: "Evidence",
  genotype: "Genotype",
  phenotype: "Phenotype",
  rule_coverage: "Rule Coverage",
};

function pct(value) {
  return `${Math.round((Number(value) || 0) * 100)}%`;
}

function ConfidenceBar({ label, value }) {
  const width = Math.max(0, Math.min(100, Math.round((Number(value) || 0) * 100)));
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs text-slate-600">
        <span>{label}</span>
        <span className="font-mono text-slate-800">{width}%</span>
      </div>
      <div className="h-2.5 rounded-full bg-slate-200 overflow-hidden">
        <div
          className="h-full rounded-full bg-gradient-to-r from-teal-700 to-emerald-600 transition-all duration-700"
          style={{ width: `${width}%` }}
        />
      </div>
    </div>
  );
}

export default function ConfidenceEvidencePanel({ results }) {
  if (!results?.length) {
    return null;
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {results.map((result, idx) => {
        const trace = result.evidence_trace;
        const components = trace?.confidence_components || {};
        const reference = trace?.cpic_reference || {};
        const annotation = trace?.pharmgkb_annotation || {};
        const decisionChain = trace?.decision_chain || [];
        return (
          <article
            key={`${result.drug}-${idx}`}
            className="glass-panel rounded-2xl p-5 border border-slate-300/70"
          >
            <header className="flex items-center justify-between gap-3 mb-4">
              <div>
                <h3 className="font-display text-lg font-semibold text-slate-900">
                  {result.drug}
                </h3>
                <p className="text-xs text-slate-600 font-mono">
                  {result.pharmacogenomic_profile?.primary_gene} • {result.pharmacogenomic_profile?.phenotype}
                </p>
              </div>
              <div className="px-2.5 py-1 rounded-md bg-teal-50 border border-teal-200 text-teal-900 text-xs font-semibold">
                Final Confidence{" "}
                {pct(
                  trace?.confidence_score_calibrated ??
                    trace?.confidence_score_v2 ??
                    result.risk_assessment?.confidence_score,
                )}
              </div>
            </header>

            <section className="space-y-3 mb-4">
              {Object.entries(LABELS).map(([key, label]) => (
                <ConfidenceBar key={key} label={label} value={components[key]} />
              ))}
            </section>

            <section className="grid gap-2 text-sm">
              <div className="flex items-start gap-2">
                <FileSearch className="w-4 h-4 mt-0.5 text-slate-500" />
                <p className="text-slate-700">
                  Rule Match:{" "}
                  <span className="font-semibold text-slate-900">
                    {trace?.rule_match ? "Yes" : "No"}
                  </span>
                </p>
              </div>
              <div className="flex items-start gap-2">
                <Microscope className="w-4 h-4 mt-0.5 text-slate-500" />
                <p className="text-slate-700">
                  Evidence Level:{" "}
                  <span className="font-semibold text-slate-900">
                    {annotation.evidence_level || "N/A"}
                  </span>
                </p>
              </div>
              <div className="flex items-start gap-2">
                <ShieldCheck className="w-4 h-4 mt-0.5 text-slate-500" />
                <p className="text-slate-700">
                  CPIC:{" "}
                  <span className="font-semibold text-slate-900">
                    {reference.guideline || "Curated CPIC mapping"}
                  </span>
                </p>
              </div>
            </section>

            {decisionChain.length > 0 && (
              <details className="mt-4 rounded-xl border border-slate-200 bg-white">
                <summary className="cursor-pointer list-none px-3 py-2 text-sm font-semibold text-slate-800">
                  View Evidence Trail ({decisionChain.length} steps)
                </summary>
                <div className="px-3 pb-3 space-y-2">
                  {decisionChain.map((step) => (
                    <div
                      key={`${result.drug}-${step.step}`}
                      className="rounded-lg border border-slate-200 bg-slate-50 p-2"
                    >
                      <p className="text-xs font-semibold text-slate-800">
                        Step {step.step}: {step.action}
                      </p>
                      <p className="text-xs text-slate-700 mt-1 break-words overflow-hidden">
                        <span className="font-medium">Input:</span>{" "}
                        <code className="whitespace-pre-wrap break-all text-[11px]">
                          {typeof step.input === "string"
                            ? step.input
                            : JSON.stringify(step.input)}
                        </code>
                      </p>
                      <p className="text-xs text-slate-700 mt-1 break-words overflow-hidden">
                        <span className="font-medium">Output:</span>{" "}
                        <code className="whitespace-pre-wrap break-all text-[11px]">
                          {typeof step.output === "string"
                            ? step.output
                            : JSON.stringify(step.output)}
                        </code>
                      </p>
                      <p className="text-xs text-slate-600 mt-1">
                        <span className="font-medium">Source:</span> {step.source}
                      </p>
                    </div>
                  ))}
                </div>
              </details>
            )}
          </article>
        );
      })}
    </div>
  );
}
