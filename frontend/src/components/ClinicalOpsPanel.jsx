import { AlertTriangle, ShieldAlert } from "lucide-react";

function riskTone(risk) {
  if (risk === "Toxic" || risk === "Ineffective") {
    return "bg-red-100 text-red-800 border-red-200";
  }
  if (risk === "Adjust Dosage" || risk === "Unknown") {
    return "bg-amber-100 text-amber-800 border-amber-200";
  }
  return "bg-emerald-100 text-emerald-800 border-emerald-200";
}

function pct(value, total) {
  if (!total) return 0;
  return Math.round((value / total) * 100);
}

export default function ClinicalOpsPanel({ results, cohortSummary }) {
  const hasResults = Array.isArray(results) && results.length > 0;
  if (!hasResults) return null;

  const total = cohortSummary?.cohort_size || results.length;
  const highRiskCount = cohortSummary?.high_risk_count || 0;

  return (
    <div className="space-y-4">
      <section className="glass-panel rounded-2xl p-5 border border-slate-300/70">
        <h3 className="text-lg font-display font-semibold text-slate-900 mb-4">
          Cohort Risk Snapshot
        </h3>
        <div className="grid md:grid-cols-3 gap-3 mb-4">
          <div className="rounded-xl border border-slate-200 bg-white p-3">
            <p className="text-xs uppercase tracking-wide text-slate-500">Cohort Size</p>
            <p className="text-2xl font-mono font-semibold text-slate-900">{total}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-3">
            <p className="text-xs uppercase tracking-wide text-slate-500">High Risk</p>
            <p className="text-2xl font-mono font-semibold text-red-700">{highRiskCount}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-3">
            <p className="text-xs uppercase tracking-wide text-slate-500">Alert</p>
            <p className="text-sm font-medium text-slate-800">
              {cohortSummary?.alert || "No cohort alert"}
            </p>
          </div>
        </div>

        <div className="space-y-3">
          {results.map((result, idx) => {
            const risk = result?.risk_assessment?.risk_label || "Unknown";
            const confidence = Math.round(
              (Number(result?.risk_assessment?.confidence_score) || 0) * 100,
            );
            return (
              <div
                key={`${result.drug}-${idx}`}
                className="rounded-xl border border-slate-200 bg-white p-3"
              >
                <div className="flex items-center justify-between gap-3 mb-2">
                  <div>
                    <p className="font-semibold text-slate-900">{result.drug}</p>
                    <p className="text-xs text-slate-600">
                      {result?.pharmacogenomic_profile?.primary_gene} •{" "}
                      {result?.pharmacogenomic_profile?.phenotype}
                    </p>
                  </div>
                  <span className={`px-2 py-1 rounded-md border text-xs font-semibold ${riskTone(risk)}`}>
                    {risk}
                  </span>
                </div>
                <div className="h-2.5 rounded-full bg-slate-200 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-teal-700"
                    style={{ width: `${confidence}%` }}
                  />
                </div>
                <p className="mt-1 text-xs text-slate-600">Confidence {confidence}%</p>
              </div>
            );
          })}
        </div>
      </section>

      <section className="glass-panel rounded-2xl p-5 border border-slate-300/70">
        <h3 className="text-lg font-display font-semibold text-slate-900 mb-4">
          Phenoconversion Alerts
        </h3>
        <div className="space-y-3">
          {results.map((result, idx) => {
            const p = result?.phenoconversion_check;
            if (!p?.phenoconversion_risk) {
              return (
                <div
                  key={`${result.drug}-pc-${idx}`}
                  className="rounded-xl border border-emerald-200 bg-emerald-50 p-3"
                >
                  <div className="flex items-center gap-2">
                    <ShieldAlert className="w-4 h-4 text-emerald-700" />
                    <p className="text-sm text-emerald-800">
                      {result.drug}: no phenoconversion risk detected.
                    </p>
                  </div>
                </div>
              );
            }

            const meds = (p.caused_by || [])
              .map((item) => `${item.drug} (${item.strength})`)
              .join(", ");
            return (
              <div
                key={`${result.drug}-pc-${idx}`}
                className="rounded-xl border border-amber-200 bg-amber-50 p-3"
              >
                <div className="flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-700 mt-0.5" />
                  <div className="text-sm text-amber-900">
                    <p className="font-semibold">
                      {result.drug}: functional phenotype shift{" "}
                      {p.genetic_phenotype} → {p.functional_phenotype}
                    </p>
                    <p className="mt-1">{p.clinical_note}</p>
                    {meds && <p className="mt-1 text-amber-800">Drivers: {meds}</p>}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
