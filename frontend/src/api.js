/**
 * API client for PharmaGuard AI backend
 */

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

/**
 * Analyze VCF file for drug interactions
 * @param {File} vcfFile - VCF file to analyze
 * @param {string[]} drugs - List of drug names
 * @param {string} patientId - Optional patient identifier
 */
export async function analyzeVCF(
  vcfFile,
  drugs,
  patientId = null,
  concurrentMedications = "",
) {
  const formData = new FormData();
  formData.append("vcf_file", vcfFile);
  formData.append("drugs", drugs.join(","));
  if (patientId) {
    formData.append("patient_id", patientId);
  }
  if (concurrentMedications && concurrentMedications.trim()) {
    formData.append("concurrent_medications", concurrentMedications.trim());
  }

  const response = await fetch(`${API_BASE}/analyze-strict`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  const strictResults = await response.json();

  const enrichedResults = await Promise.all(
    strictResults.map(async (result) => {
      try {
        const [trace, phenoconversion] = await Promise.all([
          getEvidenceTrace({
          drug: result.drug,
          gene: result.pharmacogenomic_profile?.primary_gene,
          phenotype: expandPhenotype(
            result.pharmacogenomic_profile?.phenotype,
            result.pharmacogenomic_profile?.primary_gene,
          ),
          vcf_quality: result.quality_metrics?.vcf_quality_score,
          annotation_completeness: result.quality_metrics?.annotation_completeness,
          diplotype: result.pharmacogenomic_profile?.diplotype,
          risk_label: result.risk_assessment?.risk_label,
          detected_variant_count:
            result.pharmacogenomic_profile?.detected_variants?.length || 0,
          gene_support_score:
            (result.pharmacogenomic_profile?.detected_variants?.length || 0) > 0
              ? 1.0
              : 0.7,
          calibrated_confidence: result.risk_assessment?.confidence_score,
          }),
          concurrentMedications?.trim()
            ? checkPhenoconversion({
                gene: result.pharmacogenomic_profile?.primary_gene,
                geneticPhenotype: result.pharmacogenomic_profile?.phenotype,
                concurrentMedications,
              })
            : Promise.resolve(null),
        ]);
        return { ...result, evidence_trace: trace, phenoconversion_check: phenoconversion };
      } catch {
        return { ...result, evidence_trace: null };
      }
    }),
  );

  let cohortSummary = null;
  try {
    cohortSummary = await getCohortSummary(enrichedResults);
  } catch {
    cohortSummary = null;
  }

  return {
    success: true,
    results: enrichedResults,
    cohort_summary: cohortSummary,
    errors: [],
  };
}

function expandPhenotype(abbrev, gene) {
  if ((gene || "").toUpperCase() === "SLCO1B1") {
    const slcoMap = {
      PM: "Poor Function",
      IM: "Decreased Function",
      NM: "Normal Function",
      RM: "Increased Function",
      URM: "Increased Function",
      Unknown: "Unknown",
    };
    return slcoMap[abbrev] || abbrev || "Unknown";
  }
  const map = {
    PM: "Poor Metabolizer",
    IM: "Intermediate Metabolizer",
    NM: "Normal Metabolizer",
    RM: "Rapid Metabolizer",
    URM: "Ultrarapid Metabolizer",
    Unknown: "Unknown",
  };
  return map[abbrev] || abbrev || "Unknown";
}

export async function getEvidenceTrace({
  drug,
  gene,
  phenotype,
  vcf_quality,
  annotation_completeness,
  diplotype,
  risk_label,
  detected_variant_count,
  gene_support_score,
  calibrated_confidence,
}) {
  const formData = new FormData();
  formData.append("drug", drug);
  formData.append("gene", gene);
  formData.append("phenotype", phenotype);
  if (vcf_quality !== undefined && vcf_quality !== null) {
    formData.append("vcf_quality", String(vcf_quality));
  }
  if (annotation_completeness !== undefined && annotation_completeness !== null) {
    formData.append("annotation_completeness", String(annotation_completeness));
  }
  if (diplotype) {
    formData.append("diplotype", diplotype);
  }
  if (risk_label) {
    formData.append("risk_label", risk_label);
  }
  if (detected_variant_count !== undefined && detected_variant_count !== null) {
    formData.append("detected_variant_count", String(detected_variant_count));
  }
  if (gene_support_score !== undefined && gene_support_score !== null) {
    formData.append("gene_support_score", String(gene_support_score));
  }
  if (calibrated_confidence !== undefined && calibrated_confidence !== null) {
    formData.append("calibrated_confidence", String(calibrated_confidence));
  }

  const response = await fetch(`${API_BASE}/evidence-trace`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
  return response.json();
}

export async function checkPhenoconversion({
  gene,
  geneticPhenotype,
  concurrentMedications,
}) {
  const formData = new FormData();
  formData.append("gene", gene);
  formData.append("genetic_phenotype", geneticPhenotype);
  formData.append("concurrent_medications", concurrentMedications || "");

  const response = await fetch(`${API_BASE}/phenoconversion-check`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
  return response.json();
}

export async function getCohortSummary(results) {
  const strictResults = (results || []).map((result) => {
    const { evidence_trace, phenoconversion_check, ...strictResult } = result || {};
    return strictResult;
  });
  const response = await fetch(`${API_BASE}/cohort-summary`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(strictResults),
  });

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
  return response.json();
}

/**
 * Get list of supported drugs
 */
export async function getSupportedDrugs() {
  const response = await fetch(`${API_BASE}/supported-drugs`);
  if (!response.ok) {
    throw new Error("Failed to fetch supported drugs");
  }
  return response.json();
}

/**
 * Normalize a drug name
 * @param {string} drugName - Drug name to normalize
 */
export async function normalizeDrug(drugName) {
  const formData = new FormData();
  formData.append("drug_name", drugName);

  const response = await fetch(`${API_BASE}/normalize-drug`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error("Failed to normalize drug name");
  }

  return response.json();
}

/**
 * Get sample VCF content
 * @param {string} phenotypeType - Type of sample: pm_cyp2d6, pm_cyp2c19, etc.
 */
export async function getSampleVCF(phenotypeType) {
  const response = await fetch(`${API_BASE}/sample-vcf/${phenotypeType}`);
  if (!response.ok) {
    throw new Error("Failed to fetch sample VCF");
  }
  return response.json();
}

/**
 * Check API health
 */
export async function checkHealth() {
  const response = await fetch(`${API_BASE}/health`);
  if (!response.ok) {
    throw new Error("API health check failed");
  }
  return response.json();
}
