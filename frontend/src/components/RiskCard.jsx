import {
  AlertTriangle,
  CheckCircle,
  XCircle,
  AlertOctagon,
  HelpCircle,
} from "lucide-react";

const riskConfig = {
  Safe: {
    icon: CheckCircle,
    className: "risk-safe",
    headerClass: "risk-safe-bg",
    iconColor: "text-emerald-400",
    label: "SAFE",
  },
  "Adjust Dosage": {
    icon: AlertTriangle,
    className: "risk-adjust",
    headerClass: "risk-adjust-bg",
    iconColor: "text-amber-400",
    label: "ADJUST DOSAGE",
  },
  Toxic: {
    icon: AlertOctagon,
    className: "risk-toxic",
    headerClass: "risk-toxic-bg",
    iconColor: "text-red-400",
    label: "TOXIC RISK",
  },
  Ineffective: {
    icon: XCircle,
    className: "risk-ineffective",
    headerClass: "risk-ineffective-bg",
    iconColor: "text-purple-400",
    label: "INEFFECTIVE",
  },
  Unknown: {
    icon: HelpCircle,
    className: "",
    headerClass: "risk-unknown-bg",
    iconColor: "text-slate-400",
    label: "UNKNOWN",
  },
};

export default function RiskCard({ result, index }) {
  const config =
    riskConfig[result.risk_assessment.risk_label] || riskConfig.Unknown;
  const Icon = config.icon;

  return (
    <div
      className="glass-panel overflow-hidden"
      style={{ animationDelay: `${index * 100}ms` }}
    >
      {/* Header with risk indicator */}
      <div className={`p-6 ${config.headerClass}`}>
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-2xl font-bold text-light font-[Syne] tracking-tight">
              {result.drug}
            </h3>
            <p className="text-mist text-sm mt-1">
              Primary Gene:{" "}
              <span className="text-cyan-glow font-mono">
                {result.pharmacogenomic_profile.primary_gene}
              </span>
            </p>
          </div>
          <div className={`p-3 rounded-xl ${config.className}`}>
            <Icon className="w-6 h-6" />
          </div>
        </div>

        {/* Risk badge */}
        <div className="mt-4 flex items-center gap-3">
          <span
            className={`px-4 py-1.5 rounded-full text-xs font-bold tracking-wider font-mono ${config.className}`}
          >
            {config.label}
          </span>
          <span className="text-sm text-mist">
            Confidence:{" "}
            <span className="text-light font-mono">
              {(result.risk_assessment.confidence_score * 100).toFixed(0)}%
            </span>
          </span>
        </div>
      </div>

      {/* Genetic profile */}
      <div className="p-6 border-t border-ash/30">
        <h4 className="text-xs font-bold text-cyan-glow uppercase tracking-wider mb-4">
          Pharmacogenomic Profile
        </h4>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <p className="text-xs text-mist mb-1">Diplotype</p>
            <p className="text-lg font-mono font-semibold text-light">
              {result.pharmacogenomic_profile.diplotype}
            </p>
          </div>
          <div>
            <p className="text-xs text-mist mb-1">Phenotype</p>
            <p className="text-lg font-mono font-semibold text-light">
              {result.pharmacogenomic_profile.phenotype}
            </p>
          </div>
          <div>
            <p className="text-xs text-mist mb-1">Severity</p>
            <p className="text-lg font-semibold text-light capitalize">
              {result.risk_assessment.severity}
            </p>
          </div>
        </div>
      </div>

      {/* Clinical recommendation */}
      <div className="p-6 border-t border-ash/30 bg-abyss/30">
        <h4 className="text-xs font-bold text-cyan-glow uppercase tracking-wider mb-3">
          Clinical Recommendation
        </h4>
        <p className="text-light leading-relaxed">
          {result.clinical_recommendation.action}
        </p>
        {result.clinical_recommendation.alternative_drugs?.length > 0 && (
          <div className="mt-4">
            <p className="text-xs text-mist mb-2">Alternative drugs:</p>
            <div className="flex flex-wrap gap-2">
              {result.clinical_recommendation.alternative_drugs.map((drug) => (
                <span
                  key={drug}
                  className="px-3 py-1 rounded-full bg-cyan-glow/10 text-cyan-glow text-xs font-medium"
                >
                  {drug}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* LLM Explanation (collapsible) */}
      <details className="group">
        <summary className="p-4 border-t border-ash/30 cursor-pointer hover:bg-cyan-glow/5 transition-colors flex items-center justify-between">
          <span className="text-sm font-medium text-mist group-hover:text-light transition-colors">
            View AI Analysis
          </span>
          <svg
            className="w-4 h-4 text-mist group-open:rotate-180 transition-transform"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </summary>
        <div className="p-6 border-t border-ash/30 space-y-4 bg-void/50">
          <div>
            <h5 className="text-xs font-bold text-cyan-glow uppercase tracking-wider mb-2">
              Summary
            </h5>
            <p className="text-light text-sm leading-relaxed">
              {result.llm_generated_explanation.summary}
            </p>
          </div>
          <div>
            <h5 className="text-xs font-bold text-cyan-glow uppercase tracking-wider mb-2">
              Mechanism
            </h5>
            <p className="text-cloud text-sm leading-relaxed">
              {result.llm_generated_explanation.mechanism}
            </p>
          </div>
          <div>
            <h5 className="text-xs font-bold text-cyan-glow uppercase tracking-wider mb-2">
              Patient-Friendly Explanation
            </h5>
            <p className="text-cloud text-sm leading-relaxed italic">
              "{result.llm_generated_explanation.patient_summary}"
            </p>
          </div>
        </div>
      </details>
    </div>
  );
}
