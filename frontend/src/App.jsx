import { useState, useCallback } from "react";
import {
  Dna,
  Activity,
  FlaskConical,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  Database,
  Sparkles,
} from "lucide-react";
import "./index.css";

import FileUpload from "./components/FileUpload";
import DrugInput from "./components/DrugInput";
import RiskCard from "./components/RiskCard";
import VariantTable from "./components/VariantTable";
import JsonViewer from "./components/JsonViewer";
import ConfidenceEvidencePanel from "./components/ConfidenceEvidencePanel";
import ClinicalOpsPanel from "./components/ClinicalOpsPanel";

import { analyzeVCF, getSupportedDrugs } from "./api";

function App() {
  const [vcfFile, setVcfFile] = useState(null);
  const [selectedDrugs, setSelectedDrugs] = useState([]);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("risks");
  const [concurrentMeds, setConcurrentMeds] = useState("");

  const clearSelectedFile = useCallback(() => {
    setVcfFile(null);
  }, []);

  const handleAnalyze = useCallback(async () => {
    if (!vcfFile || selectedDrugs.length === 0) {
      setError("Please upload a VCF file and select at least one drug");
      return;
    }

    setIsAnalyzing(true);
    setError(null);
    setAnalysisResult(null);

    try {
      const result = await analyzeVCF(vcfFile, selectedDrugs, null, concurrentMeds);
      setAnalysisResult(result);
      if (!result.success && result.errors?.length) {
        setError(result.errors.join(" | "));
      }
      setActiveTab("risks");
    } catch (err) {
      setError(err.message || "Analysis failed. Please try again.");
    } finally {
      setIsAnalyzing(false);
    }
  }, [vcfFile, selectedDrugs, concurrentMeds]);

  const canAnalyze = vcfFile && selectedDrugs.length > 0 && !isAnalyzing;
  const analysisResults = analysisResult?.results || [];
  const cohortSummary = analysisResult?.cohort_summary || null;
  const strictJsonPayload = analysisResult
    ? {
        success: analysisResult.success,
        results: analysisResults.map((result) => {
          const { evidence_trace, phenoconversion_check, ...strictResult } = result;
          return strictResult;
        }),
        errors: analysisResult.errors || [],
      }
    : null;
  const allDetectedVariants = analysisResults.flatMap(
    (result) => result.pharmacogenomic_profile?.detected_variants || [],
  );

  return (
    <div className="app-container min-h-screen bg-transparent text-slate-900">
      {/* Molecular grid background */}
      <div className="molecular-grid fixed inset-0 pointer-events-none opacity-30" />

      {/* Header */}
      <header className="relative z-10 border-b border-slate-300/70 backdrop-blur-xl bg-white/85">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="relative">
                <div className="absolute inset-0 bg-accent/40 blur-xl rounded-full" />
                <div className="relative w-12 h-12 rounded-xl bg-gradient-to-br from-accent/20 to-accent/5 border border-accent/30 flex items-center justify-center">
                  <Dna className="w-6 h-6 text-accent" />
                </div>
              </div>
              <div>
                <h1 className="text-2xl font-display font-bold tracking-tight">
                  Pharma<span className="text-accent">Guard</span> AI
                </h1>
                <p className="text-sm text-slate-600 font-mono">
                  Pharmacogenomics Risk Analysis Platform
                </p>
              </div>
            </div>

            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-accent/10 border border-accent/20">
                <Activity className="w-4 h-4 text-accent animate-pulse" />
                <span className="text-sm font-mono text-accent">RIFT 2026</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="relative z-10 max-w-7xl mx-auto px-6 py-8">
        {/* Input Section */}
        <section className="grid md:grid-cols-2 gap-6 mb-8">
          {/* File Upload */}
          <div className="glass-panel rounded-2xl p-6">
            <div className="flex items-center gap-3 mb-4">
              <Database className="w-5 h-5 text-accent" />
              <h2 className="text-lg font-display font-semibold">
                Genomic Data
              </h2>
            </div>
            <FileUpload
              onFileSelect={setVcfFile}
              selectedFile={vcfFile}
              onClear={clearSelectedFile}
            />
          </div>

          {/* Drug Selection */}
          <div className="glass-panel rounded-2xl p-6">
            <div className="flex items-center gap-3 mb-4">
              <FlaskConical className="w-5 h-5 text-accent" />
              <h2 className="text-lg font-display font-semibold">
                Drug Selection
              </h2>
            </div>
            <DrugInput
              selectedDrugs={selectedDrugs}
              onDrugsChange={setSelectedDrugs}
              fetchDrugs={getSupportedDrugs}
            />
            <div className="mt-4">
              <label className="block text-xs font-semibold tracking-wide text-slate-600 mb-2">
                Concurrent Medications (optional, comma-separated)
              </label>
              <input
                type="text"
                value={concurrentMeds}
                onChange={(event) => setConcurrentMeds(event.target.value)}
                placeholder="e.g. fluoxetine, omeprazole"
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-200"
              />
            </div>
          </div>
        </section>

        {/* Analyze Button */}
        <section className="flex justify-center mb-8">
          <button
            onClick={handleAnalyze}
            disabled={!canAnalyze}
            className={`
              relative group px-8 py-4 rounded-xl font-display font-semibold text-lg
              transition-all duration-300 overflow-hidden
              ${
                canAnalyze
                  ? "bg-accent text-void hover:shadow-[0_0_40px_rgba(0,229,199,0.4)] hover:scale-105"
                  : "bg-slate-200 text-slate-400 cursor-not-allowed"
              }
            `}
          >
            <span className="relative z-10 flex items-center gap-3">
              {isAnalyzing ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Analyzing Genome...
                </>
              ) : (
                <>
                  <Sparkles className="w-5 h-5" />
                  Run Analysis
                </>
              )}
            </span>
            {canAnalyze && (
              <div className="absolute inset-0 bg-gradient-to-r from-accent via-white/20 to-accent opacity-0 group-hover:opacity-100 transition-opacity duration-500 blur-xl" />
            )}
          </button>
        </section>

        {/* Error Display */}
        {error && (
          <div className="mb-8 p-4 rounded-xl bg-red-500/10 border border-red-500/30 flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-red-400 shrink-0" />
            <p className="text-red-300">{error}</p>
          </div>
        )}

        {/* Results Section */}
        {analysisResult && (
          <section className="space-y-6">
            {/* Result Header */}
            <div className="glass-panel rounded-2xl p-6">
              <div className="flex items-center justify-between flex-wrap gap-4">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-xl bg-accent/10 border border-accent/30 flex items-center justify-center">
                    <CheckCircle2 className="w-6 h-6 text-accent" />
                  </div>
                  <div>
                    <h2 className="text-xl font-display font-bold">
                      Analysis Complete
                    </h2>
                    <p className="text-slate-600 text-sm font-mono">
                      Session:{" "}
                      {analysisResults[0]?.patient_id || "unknown"}
                    </p>
                  </div>
                </div>

                <div className="flex gap-4 text-sm">
                  <div className="px-4 py-2 rounded-lg bg-slate-100/70 border border-slate-300/70">
                    <span className="text-slate-600">Drugs Analyzed</span>
                    <p className="text-lg font-mono font-bold text-accent">
                      {analysisResults.length}
                    </p>
                  </div>
                  <div className="px-4 py-2 rounded-lg bg-slate-100/70 border border-slate-300/70">
                    <span className="text-slate-600">Variants Found</span>
                    <p className="text-lg font-mono font-bold text-accent">
                      {allDetectedVariants.length}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Tabs */}
            <div className="flex gap-2 p-1 bg-slate-200/70 rounded-xl w-fit">
              {[
                { id: "risks", label: "Risk Analysis", icon: AlertTriangle },
                { id: "variants", label: "Variants", icon: Dna },
                { id: "evidence", label: "Evidence", icon: Activity },
                { id: "ops", label: "Clinical Ops", icon: Sparkles },
                { id: "json", label: "Raw JSON", icon: Database },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`
                    flex items-center gap-2 px-4 py-2 rounded-lg transition-all duration-200
                    ${
                      activeTab === tab.id
                        ? "bg-accent text-void font-semibold"
                        : "text-slate-600 hover:text-slate-900 hover:bg-white/80"
                    }
                  `}
                >
                  <tab.icon className="w-4 h-4" />
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Tab Content */}
            <div className="min-h-[400px]">
              {activeTab === "risks" && (
                <div className="grid gap-4 md:grid-cols-2">
                  {analysisResults.map((result, idx) => (
                    <RiskCard key={`${result.drug}-${idx}`} result={result} index={idx} />
                  ))}
                </div>
              )}

              {activeTab === "variants" && (
                <VariantTable variants={allDetectedVariants} />
              )}

              {activeTab === "evidence" && (
                <ConfidenceEvidencePanel results={analysisResults} />
              )}

              {activeTab === "ops" && (
                <ClinicalOpsPanel
                  results={analysisResults}
                  cohortSummary={cohortSummary}
                />
              )}

              {activeTab === "json" && (
                <JsonViewer
                  data={strictJsonPayload}
                  title="Required JSON Output (Strict Contract)"
                />
              )}
            </div>
          </section>
        )}

        {/* Empty State */}
        {!analysisResult && !isAnalyzing && (
          <section className="flex flex-col items-center justify-center py-20 text-center">
            <div className="relative mb-6">
              <div className="absolute inset-0 bg-accent/20 blur-3xl rounded-full" />
              <div className="relative w-24 h-24 rounded-2xl bg-gradient-to-br from-accent/20 to-accent/5 border border-accent/20 flex items-center justify-center">
                <Dna className="w-12 h-12 text-accent/60" />
              </div>
            </div>
            <h3 className="text-xl font-display font-semibold text-slate-800 mb-2">
              Ready for Analysis
            </h3>
            <p className="text-slate-600 max-w-md">
              Upload a VCF file and select the medications to analyze. Our
              AI-powered pipeline will identify pharmacogenomic risks and
              generate personalized recommendations.
            </p>
          </section>
        )}
      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t border-slate-300/70 mt-auto">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between text-sm text-slate-600">
            <p className="font-mono">
              PharmaGuard AI v1.0 | RIFT 2026 Hackathon
            </p>
            <p>Powered by CPIC Guidelines & PharmGKB</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
