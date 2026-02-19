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
export async function analyzeVCF(vcfFile, drugs, patientId = null) {
  const formData = new FormData();
  formData.append("vcf_file", vcfFile);
  formData.append("drugs", drugs.join(","));
  if (patientId) {
    formData.append("patient_id", patientId);
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
  return {
    success: true,
    results: strictResults,
    errors: [],
  };
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
