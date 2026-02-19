"""
Stage 6: LLM Explainer - Dual LLM Architecture (Vertex AI dedicated endpoints)

Stage A - MedGemma    (europe-west4, project 452689003903)
Stage B - FunctionGemma (us-east4,   project 452689003903)

The dedicated endpoints require their own DNS domain. Windows ISP DNS often
cannot resolve *.prediction.vertexai.goog, so we resolve via Google Public
DNS (8.8.8.8) and override socket.getaddrinfo for just those hosts. SSL
verification still works because urllib3 sends the original hostname via SNI.
"""

import asyncio
import base64
import json
import logging
import os
import socket
import tempfile
import threading
from typing import Dict, List, Optional, Union

import dns.resolver
import requests as _requests
import google.auth
import google.auth.transport.requests
from google.cloud import aiplatform
from google.protobuf import json_format
from google.protobuf.struct_pb2 import Value

from models.schemas import DetectedVariant, LLMGeneratedExplanation, RiskAssessment
from pipeline.rules_loader import get_rules

logger = logging.getLogger(__name__)
_RULES = get_rules()

# ---------------------------------------------------------------------------
# Bootstrap credentials from GOOGLE_CREDENTIALS_BASE64 if provided
# ---------------------------------------------------------------------------
_creds_b64 = os.getenv("GOOGLE_CREDENTIALS_BASE64", "")
if _creds_b64 and not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    try:
        _creds_json = base64.b64decode(_creds_b64).decode("utf-8")
        _tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, prefix="gcp_sa_"
        )
        _tmp.write(_creds_json)
        _tmp.flush()
        _tmp.close()
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = _tmp.name
        logger.info(f"Loaded GCP credentials from GOOGLE_CREDENTIALS_BASE64 -> {_tmp.name}")
    except Exception as _e:
        logger.warning(f"Failed to decode GOOGLE_CREDENTIALS_BASE64: {_e}")

# ---------------------------------------------------------------------------
# Configuration  (project NUMBER as required by gapic / REST predict API)
# ---------------------------------------------------------------------------
_PROJECT = os.getenv("VERTEX_PROJECT_NUMBER", "452689003903")

_MEDGEMMA_ENDPOINT_ID  = os.getenv("MEDGEMMA_ENDPOINT_ID",  "mg-endpoint-b7530683-a8ac-4651-9e0b-f6bd1e8f1c7b")
_MEDGEMMA_LOCATION     = os.getenv("MEDGEMMA_LOCATION",     "europe-west4")
_MEDGEMMA_DOMAIN       = os.getenv("MEDGEMMA_DEDICATED_DOMAIN", "2384381124785733632.europe-west4-452689003903.prediction.vertexai.goog")

_FUNCGEMMA_ENDPOINT_ID = os.getenv("FUNCGEMMA_ENDPOINT_ID", "mg-endpoint-9b93b690-ff5f-4625-b2d6-ef87833e51b7")
_FUNCGEMMA_LOCATION    = os.getenv("FUNCGEMMA_LOCATION",    "us-east4")
_FUNCGEMMA_DOMAIN      = os.getenv("FUNCGEMMA_DEDICATED_DOMAIN", "mg-endpoint-9b93b690-ff5f-4625-b2d6-ef87833e51b7.us-east4-998066007895.prediction.vertexai.goog")


# ---------------------------------------------------------------------------
# DNS override: resolve *.vertexai.goog via Google Public DNS (8.8.8.8)
# so Windows ISP DNS failures are bypassed. SSL SNI still uses original host.
# ---------------------------------------------------------------------------
_dns_lock = threading.Lock()
_dns_cache: Dict[str, str] = {}          # hostname -> resolved IP
_original_getaddrinfo = socket.getaddrinfo


def _resolve_via_google_dns(hostname: str) -> Optional[str]:
    """Resolve hostname using Google Public DNS 8.8.8.8. Returns IP or None."""
    if hostname in _dns_cache:
        return _dns_cache[hostname]
    try:
        resolver = dns.resolver.Resolver()
        resolver.nameservers = ["8.8.8.8", "8.8.4.4"]
        resolver.timeout = 5
        resolver.lifetime = 10
        answers = resolver.resolve(hostname, "A")
        ip = str(answers[0])
        _dns_cache[hostname] = ip
        logger.info(f"Resolved {hostname} -> {ip} via Google DNS")
        return ip
    except Exception as e:
        logger.warning(f"Google DNS resolution failed for {hostname}: {e}")
        return None


def _patched_getaddrinfo(host, port, *args, **kwargs):
    if host in _dns_cache:
        host = _dns_cache[host]
    return _original_getaddrinfo(host, port, *args, **kwargs)


def _install_dns_override(*hostnames: str) -> None:
    """Resolve given hostnames via 8.8.8.8 and patch socket.getaddrinfo."""
    with _dns_lock:
        changed = False
        for hostname in hostnames:
            if hostname and hostname not in _dns_cache:
                _resolve_via_google_dns(hostname)
                changed = True
        if changed or socket.getaddrinfo is not _patched_getaddrinfo:
            socket.getaddrinfo = _patched_getaddrinfo  # idempotent


# Pre-resolve dedicated domains at module load (if provided)
try:
    _install_dns_override(_MEDGEMMA_DOMAIN, _FUNCGEMMA_DOMAIN)
except Exception:
    pass


# ---------------------------------------------------------------------------
# Predict via REST — works for both dedicated and shared-domain endpoints
#
# Dedicated endpoint URL:  https://{dedicated_domain}/v1/endpoints/{id}:predict
# Shared endpoint URL:     https://{location}-aiplatform.googleapis.com/v1/projects/{proj}/locations/{loc}/endpoints/{id}:predict
# ---------------------------------------------------------------------------

_auth_creds = None
_auth_req   = None

def _get_token() -> str:
    global _auth_creds, _auth_req
    if _auth_creds is None:
        _auth_creds, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        _auth_req = google.auth.transport.requests.Request()
    _auth_creds.refresh(_auth_req)
    return _auth_creds.token


def predict_endpoint(
    project: str,
    endpoint_id: str,
    instances: Union[Dict, List[Dict]],
    location: str,
    dedicated_domain: str = "",
) -> List:
    """Call a Vertex AI endpoint (dedicated or shared) via REST."""
    instances = instances if isinstance(instances, list) else [instances]

    shared_url = (
        f"https://{location}-aiplatform.googleapis.com"
        f"/v1/projects/{project}/locations/{location}/endpoints/{endpoint_id}:predict"
    )
    dedicated_url = (
        f"https://{dedicated_domain}/v1/projects/{project}/locations/{location}/endpoints/{endpoint_id}:predict"
        if dedicated_domain else ""
    )
    url = dedicated_url or shared_url

    token = _get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    body = {"instances": instances}

    resp = _requests.post(url, headers=headers, json=body, timeout=60)
    if dedicated_url and resp.status_code == 404:
        logger.warning(
            f"Dedicated endpoint returned 404 for {endpoint_id} at {dedicated_domain}; "
            "retrying via shared Vertex URL."
        )
        resp = _requests.post(shared_url, headers=headers, json=body, timeout=60)
    if not resp.ok:
        err_text = (resp.text or "").strip()
        if len(err_text) > 1500:
            err_text = err_text[:1500] + "...[truncated]"
        logger.error(
            "Vertex predict failed "
            f"(status={resp.status_code}, endpoint_id={endpoint_id}, location={location}, url={url}). "
            f"Response body: {err_text}"
        )
    resp.raise_for_status()
    return resp.json().get("predictions", [])


def _extract_text(predictions: List) -> str:
    if not predictions:
        return ""
    first = predictions[0]
    if isinstance(first, dict):
        return first.get("content", first.get("output", first.get("generated_text", str(first))))
    if hasattr(first, "fields"):
        for key in ("content", "output", "generated_text"):
            if key in first.fields:
                return first.fields[key].string_value
    return str(first)


def _parse_json(text: str) -> Optional[Dict]:
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1][4:] if parts[1].startswith("json") else parts[1]
    try:
        s, e = text.find("{"), text.rfind("}") + 1
        if s >= 0 and e > s:
            return json.loads(text[s:e])
    except (json.JSONDecodeError, ValueError):
        pass
    return None


def _is_placeholder_text(value: Optional[str]) -> bool:
    if value is None:
        return True
    s = str(value).strip().strip('"').strip("'").lower()
    if not s:
        return True
    placeholders = {
        "...",
        "…",
        "n/a",
        "na",
        "tbd",
        "placeholder",
        "not provided",
        "not available",
        "unknown",
    }
    return s in placeholders or s.startswith("...")


def _prefer_text(primary: Optional[str], fallback: str) -> str:
    if _is_placeholder_text(primary):
        return fallback
    return str(primary).strip()


# ---------------------------------------------------------------------------
# Main explainer class
# ---------------------------------------------------------------------------

class LLMExplainer:
    def __init__(self) -> None:
        self.enabled = os.getenv("ENABLE_LLM_EXPLANATIONS", "true").lower() == "true"

    async def generate_explanation(
        self,
        drug: str,
        gene: str,
        diplotype: str,
        phenotype: str,
        risk_assessment: RiskAssessment,
        detected_variants: list[DetectedVariant],
        cpic_action: str,
    ) -> LLMGeneratedExplanation:
        if self.enabled:
            try:
                return await self._generate_vertex_explanation(
                    drug, gene, diplotype, phenotype,
                    risk_assessment, detected_variants, cpic_action,
                )
            except Exception as exc:
                logger.warning(f"Vertex AI explanation failed: {exc}. Using template fallback.")
        return self._generate_template_explanation(
            drug, gene, diplotype, phenotype,
            risk_assessment, detected_variants, cpic_action,
        )

    async def _generate_vertex_explanation(
        self,
        drug: str,
        gene: str,
        diplotype: str,
        phenotype: str,
        risk_assessment: RiskAssessment,
        detected_variants: list[DetectedVariant],
        cpic_action: str,
    ) -> LLMGeneratedExplanation:
        template_fallback = self._generate_template_explanation(
            drug, gene, diplotype, phenotype, risk_assessment, detected_variants, cpic_action
        )
        variant_str = (
            ", ".join(f"{v.rsid} ({v.star_allele}, {v.function or 'unknown function'})" for v in detected_variants)
            if detected_variants else "No specific variants detected"
        )

        # ── Stage A: MedGemma ─────────────────────────────────────────
        prompt_a = (
            "You are a clinical pharmacogenomics expert.\n\n"
            f"Patient genomic data:\n"
            f"  Gene: {gene}\n  Diplotype: {diplotype}\n  Phenotype: {phenotype}\n"
            f"  Detected variants: {variant_str}\n  Drug analyzed: {drug}\n"
            f"  Risk level: {risk_assessment.risk_label} (severity: {risk_assessment.severity})\n"
            f"  CPIC recommended action: {cpic_action}\n\n"
            "Write a concise clinical pharmacogenomics report covering:\n"
            "1. Summary (2-3 sentences citing rsIDs and diplotype)\n"
            f"2. Biological mechanism of {gene} on {drug} metabolism\n"
            f"3. Impact of {diplotype} on enzyme function\n"
            "4. Clinical action / dosing guidance\n"
            "5. Patient-friendly version (plain language, max 3 sentences)\n"
        )

        try:
            medgemma_preds = await asyncio.to_thread(
                predict_endpoint,
                _PROJECT,
                _MEDGEMMA_ENDPOINT_ID,
                {"prompt": prompt_a},
                _MEDGEMMA_LOCATION,
                _MEDGEMMA_DOMAIN,
            )
            narrative = _extract_text(medgemma_preds)
            logger.info(f"MedGemma narrative: {len(narrative)} chars")
        except Exception as med_exc:
            logger.warning(
                f"MedGemma stage failed ({med_exc}); falling back to FunctionGemma for stage A narrative."
            )
            fallback_preds = await asyncio.to_thread(
                predict_endpoint,
                _PROJECT,
                _FUNCGEMMA_ENDPOINT_ID,
                {"prompt": prompt_a},
                _FUNCGEMMA_LOCATION,
                _FUNCGEMMA_DOMAIN,
            )
            narrative = _extract_text(fallback_preds)
            logger.info(f"FunctionGemma fallback narrative: {len(narrative)} chars")

        # ── Stage B: FunctionGemma ────────────────────────────────────
        prompt_b = (
            "Extract structured information from the following clinical pharmacogenomics report "
            "and return ONLY a valid JSON object with exactly these keys:\n"
            '{"summary": "...", "mechanism": "...", "variant_impact": "...", '
            '"clinical_context": "...", "patient_summary": "..."}\n\n'
            f"Report:\n{narrative}\n\nRespond with ONLY the JSON object, no markdown fences."
        )

        funcgemma_preds = await asyncio.to_thread(
            predict_endpoint,
            _PROJECT,
            _FUNCGEMMA_ENDPOINT_ID,
            {"prompt": prompt_b},
            _FUNCGEMMA_LOCATION,
            _FUNCGEMMA_DOMAIN,
        )
        structured_text = _extract_text(funcgemma_preds)
        logger.info(f"FunctionGemma output: {len(structured_text)} chars")

        parsed = _parse_json(structured_text)
        if parsed:
            return LLMGeneratedExplanation(
                summary=_prefer_text(parsed.get("summary"), template_fallback.summary),
                mechanism=_prefer_text(parsed.get("mechanism"), template_fallback.mechanism),
                variant_impact=_prefer_text(parsed.get("variant_impact"), template_fallback.variant_impact),
                clinical_context=_prefer_text(parsed.get("clinical_context"), template_fallback.clinical_context),
                patient_summary=_prefer_text(parsed.get("patient_summary"), template_fallback.patient_summary),
            )

        logger.warning("FunctionGemma JSON parse failed; using narrative directly.")
        return LLMGeneratedExplanation(
            summary=_prefer_text(narrative[:500] if narrative else "", template_fallback.summary),
            mechanism=template_fallback.mechanism,
            variant_impact=template_fallback.variant_impact,
            clinical_context=template_fallback.clinical_context,
            patient_summary=template_fallback.patient_summary,
        )

    # ------------------------------------------------------------------
    # Template fallback
    # ------------------------------------------------------------------

    def _generate_template_explanation(
        self,
        drug: str, gene: str, diplotype: str, phenotype: str,
        risk_assessment: RiskAssessment,
        detected_variants: list[DetectedVariant],
        cpic_action: str,
    ) -> LLMGeneratedExplanation:
        variant_refs = [f"{v.rsid} ({v.star_allele})" for v in detected_variants]
        variant_str = ", ".join(variant_refs) if variant_refs else "reference alleles"

        mechanisms = {
            "CYP2D6": f"{gene} metabolises ~25% of clinically used drugs including opioids, antidepressants, and antipsychotics.",
            "CYP2C19": f"{gene} metabolises clopidogrel into its active antiplatelet form. Reduced activity increases cardiovascular risk.",
            "CYP2C9": f"{gene} is the primary enzyme for warfarin metabolism. Reduced activity raises plasma concentrations and bleeding risk.",
            "SLCO1B1": f"{gene} encodes the OATP1B1 hepatic transporter for statins. Reduced transport increases myopathy risk.",
            "TPMT": f"{gene} catalyses methylation of thiopurines. Deficiency causes severe myelosuppression.",
            "DPYD": f"{gene} is rate-limiting in fluoropyrimidine catabolism. Deficiency causes potentially fatal toxicity.",
        }
        phenotype_impacts = {
            "Poor Metabolizer": f"The {diplotype} diplotype results in complete/near-complete loss of {gene} activity.",
            "Intermediate Metabolizer": f"The {diplotype} diplotype reduces {gene} activity to ~50% of normal.",
            "Normal Metabolizer": f"The {diplotype} diplotype confers normal {gene} activity.",
            "Rapid Metabolizer": f"The {diplotype} diplotype results in increased {gene} activity.",
            "Ultrarapid Metabolizer": f"The {diplotype} diplotype results in significantly increased {gene} activity, often from gene duplication.",
        }

        rl = risk_assessment.risk_label
        if rl == "Toxic":
            summary = f"Patient carries {diplotype} ({gene}), classified as {phenotype}. {risk_assessment.severity.capitalize()} toxicity risk for {drug}. Variants: {variant_str}."
            patient_summary = f"Your genetic test shows your body cannot safely process {drug}. Ask your doctor for an alternative."
        elif rl == "Ineffective":
            summary = f"Patient carries {diplotype} ({gene}), classified as {phenotype}. {drug} predicted ineffective. Variants: {variant_str}."
            patient_summary = f"Your genetic test shows {drug} will not work well for you. Ask your doctor for an alternative."
        elif rl == "Adjust Dosage":
            summary = f"Patient carries {diplotype} ({gene}), classified as {phenotype}. Dosage modification recommended for {drug}. Variants: {variant_str}."
            patient_summary = f"Your genetic test shows you may need a different dose of {drug}."
        else:
            summary = f"Patient carries {diplotype} ({gene}), classified as {phenotype}. Standard dosing of {drug} is appropriate. Variants: {variant_str}."
            patient_summary = f"{drug} should work normally for you at standard doses."

        ref = _RULES.cpic_references.get(f"{gene}_{drug}", {})
        clinical_context = (
            f"{cpic_action} Reference: {ref.get('authors','')} ({ref.get('year','')}). PMID: {ref.get('pmid','')}."
            if ref else cpic_action
        )
        return LLMGeneratedExplanation(
            summary=summary,
            mechanism=mechanisms.get(gene, f"{gene} affects the metabolism of {drug}."),
            variant_impact=phenotype_impacts.get(phenotype, f"The {diplotype} diplotype affects {gene} enzyme function."),
            clinical_context=clinical_context,
            patient_summary=patient_summary,
        )

    async def close(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Module-level convenience API
# ---------------------------------------------------------------------------

_explainer: Optional[LLMExplainer] = None


def get_explainer() -> LLMExplainer:
    global _explainer
    if _explainer is None:
        _explainer = LLMExplainer()
    return _explainer


async def generate_explanation(
    drug: str, gene: str, diplotype: str, phenotype: str,
    risk_assessment: RiskAssessment,
    detected_variants: List[DetectedVariant],
    cpic_action: str,
) -> LLMGeneratedExplanation:
    return await get_explainer().generate_explanation(
        drug, gene, diplotype, phenotype,
        risk_assessment, detected_variants, cpic_action,
    )
