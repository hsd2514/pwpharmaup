# 🧬 PharmaGuard AI

> **Pharmacogenomics Risk Analysis Platform** — RIFT 2026 Hackathon

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev/)
[![TailwindCSS](https://img.shields.io/badge/Tailwind_v4-06B6D4?style=flat&logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)

PharmaGuard AI is an intelligent pharmacogenomics platform that analyzes genetic variants from VCF files to predict drug response risks, generate clinical recommendations, and provide AI-powered explanations for patients and healthcare providers.

---

## 🔬 Pipeline Architecture

The system implements a 7-stage sequential processing pipeline:

```
VCF File → [Parser] → [Variant Extractor] → [Phenotype Engine] → [PharmGKB Lookup] → [Risk Engine] → [LLM Explainer] → Analysis Result
              ↓               ↓                    ↓                    ↓                  ↓               ↓
         Quality Filter   Star Alleles      Activity Scores      Drug Annotations     Risk Level      AI Narratives
```

| Stage | Module                 | Description                                              |
| ----- | ---------------------- | -------------------------------------------------------- |
| 1     | `vcf_parser.py`        | Parse VCF files, extract variants, apply quality filters |
| 2     | `variant_extractor.py` | Map variants to star alleles and diplotypes              |
| 3     | `pypgx_engine.py`      | Calculate activity scores and metabolizer phenotypes     |
| 4     | `pharmgkb_lookup.py`   | Fetch drug annotations from PharmGKB/CPIC data           |
| 5     | `risk_engine.py`       | Assess risk levels and generate clinical recommendations |
| 6     | `llm_explainer.py`     | Generate AI explanations for patients and clinicians     |
| 7     | `schemas.py`           | Validate output with Pydantic v2 models                  |

---

## 📂 Project Structure

```
pwioi/
├── backend/
│   ├── main.py                 # FastAPI application
│   ├── requirements.txt        # Python dependencies
│   ├── Dockerfile              # Backend container
│   ├── models/
│   │   ├── schemas.py          # Pydantic models
│   │   └── constants.py        # Gene mappings, drug data
│   └── pipeline/
│       ├── vcf_parser.py       # Stage 1
│       ├── variant_extractor.py # Stage 2
│       ├── pypgx_engine.py     # Stage 3
│       ├── pharmgkb_lookup.py  # Stage 4
│       ├── risk_engine.py      # Stage 5
│       └── llm_explainer.py    # Stage 6
├── frontend/
│   ├── src/
│   │   ├── App.jsx             # Main application
│   │   ├── api.js              # API client
│   │   ├── index.css           # Tailwind v4 theme
│   │   └── components/
│   │       ├── FileUpload.jsx  # VCF upload
│   │       ├── DrugInput.jsx   # Drug selection
│   │       ├── RiskCard.jsx    # Risk display
│   │       ├── VariantTable.jsx # Variant table
│   │       └── JsonViewer.jsx  # JSON output
│   ├── Dockerfile              # Frontend container
│   └── nginx.conf              # Production server
├── sample_vcf/                 # Test VCF files
├── docker-compose.yml          # Multi-container setup
├── .env.example                # Environment template
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- npm or pnpm

### Option 1: Local Development

**Backend:**

```powershell
cd backend
uv sync
uv run uvicorn main:app --reload --port 8000
```

**Frontend:**

```powershell
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173)

### Option 2: Docker Compose

```powershell
# Copy environment file
cp .env.example .env

# Edit .env and add your HuggingFace API key
notepad .env

# Start all services
docker-compose up --build
```

---

## 🧪 Sample VCF Files

The `sample_vcf/` directory contains test files for different scenarios:

| File             | Scenario                 | Expected Result                 |
| ---------------- | ------------------------ | ------------------------------- |
| `pm_cyp2d6.vcf`  | CYP2D6 Poor Metabolizer  | High risk for codeine, tramadol |
| `pm_cyp2c19.vcf` | CYP2C19 Poor Metabolizer | High risk for clopidogrel       |
| `im_cyp2c9.vcf`  | CYP2C9 Intermediate      | Moderate risk for warfarin      |
| `dpyd_im.vcf`    | DPYD Deficient           | High risk for fluorouracil      |
| `normal_all.vcf` | Normal Metabolizer       | Standard dosing for all drugs   |

---

## 🔌 API Endpoints

| Method | Endpoint                 | Description          |
| ------ | ------------------------ | -------------------- |
| `POST` | `/analyze`               | Analyze VCF + drugs  |
| `POST` | `/analyze-strict`        | Strict evaluator mode (returns `AnalysisResult[]`) |
| `POST` | `/evidence-trace`        | Deterministic rule/evidence provenance for a decision |
| `POST` | `/explanation-quality`   | Deterministic explanation quality score + fail reasons |
| `POST` | `/cohort-summary`        | Cohort-level risk matrix and high-risk patient list |
| `POST` | `/normalize-drug`        | Normalize drug name  |
| `POST` | `/phenoconversion-check` | Check inhibitor-driven phenotype shift |
| `GET`  | `/supported-drugs`       | List available drugs |
| `GET`  | `/sample-vcf/{phenotype_type}` | Download sample VCF by type (`pm_cyp2d6`, `pm_cyp2c19`, `im_cyp2c9`, `dpyd_im`, `normal_all`) |
| `GET`  | `/health`                | Health check         |

### Example Request

```bash
curl -X POST http://localhost:8000/analyze \
  -F "vcf_file=@sample_vcf/pm_cyp2d6.vcf" \
  -F "drugs=codeine" \
  -F "concurrent_medications=fluoxetine,omeprazole"
```

`concurrent_medications` is optional and enables phenoconversion detection.

---

## 🎨 Frontend Design

The UI follows a **biotech laboratory aesthetic**:

- **Color Palette:** clinical light neutrals + teal accents for medical readability
- **Typography:** Syne (display), DM Sans (body), JetBrains Mono (data)
- **Effects:** Glass panels, molecular grid background, conservative motion
- **Risk Badges:** Color-coded severity indicators (green/yellow/orange/red)

---

## ⚙️ Configuration

| Variable                  | Description                  | Default               |
| ------------------------- | ---------------------------- | --------------------- |
| `HUGGINGFACE_API_KEY`     | API key for LLM explanations | Required              |
| `BACKEND_PORT`            | Backend server port          | 8000                  |
| `VITE_API_URL`            | Frontend API endpoint        | http://localhost:8000 |
| `MIN_VARIANT_QUALITY`     | Minimum QUAL score           | 20                    |
| `ENABLE_LLM_EXPLANATIONS` | Enable AI explanations       | true                  |

---

## 📦 Dependency Management (uv)

Backend dependencies are managed via:
- `backend/pyproject.toml`
- `backend/uv.lock`

Primary commands:
```powershell
cd backend
uv sync
uv run python -m unittest discover -s tests -v
```

`requirements.txt` is kept only for compatibility with platforms that explicitly require it.

---

## 📋 Supported Genes & Drugs

### Genes

- **CYP2D6** — codeine
- **CYP2C19** — clopidogrel
- **CYP2C9** — warfarin
- **DPYD** — fluorouracil
- **TPMT** — azathioprine
- **SLCO1B1** — simvastatin

### Risk Levels

- 🟢 **Low** — Standard dosing, no adjustments needed
- 🟡 **Moderate** — Minor adjustments, routine monitoring
- 🟠 **High** — Significant adjustments, enhanced monitoring
- 🔴 **Critical** — Avoid drug or use alternative therapy

---

## ✅ Implemented Features Checklist

- 7-stage pipeline implemented end-to-end (VCF -> risk -> explanation -> schema validation)
- Dual-LLM explanation chain with robust template fallback
- Externalized clinical rules (`backend/data/clinical_rules/rules.v1.json`)
- Component-based deterministic confidence scoring (evidence + genotype + phenotype + rule coverage)
- Dashboard Evidence tab with confidence component graph and provenance metadata
- Strict endpoint for evaluator compatibility (`/analyze-strict`)
- Golden backend tests for core drug/gene scenarios
- Deterministic evidence trace endpoint (`/evidence-trace`) for scientific auditability
- Scientific-method implementation log (`SCIENTIFIC_METHOD_LOG.md`)
- Fixture-based strict snapshot conformance test (`backend/tests/fixtures`)
- Deterministic explanation quality scorer (`/explanation-quality`)
- Confidence calibration evaluation script (`backend/scripts/evaluate_confidence_calibration.py`)
- Phenoconversion detector with concurrent medication support
- Enhanced evidence trace with step-by-step `decision_chain`
- Cohort summary endpoint for multi-patient risk heatmap backends

---

## 🧾 Scientific Claim Guardrails

- Claims matrix: `CLAIMS_MATRIX.md`
- Research-to-implementation evidence log: `RESEARCH_EVIDENCE_LOG.md`
- Experiment log and implementation trace: `SCIENTIFIC_METHOD_LOG.md`

Policy used in this repo:
- confidence weights are treated as evidence-informed priors with calibration (not directly paper-fitted constants)
- phenoconversion behavior is documented to match code-level downgrade rules
- impact statements are phrased as trial-context outcomes, not deterministic population guarantees

---

## 📜 Data Sources

- **CPIC Guidelines** — [cpicpgx.org](https://cpicpgx.org/)
- **PharmGKB** — [pharmgkb.org](https://www.pharmgkb.org/)
- **PharmVar** — [pharmvar.org](https://www.pharmvar.org/)

---

## 🤝 Team

**RIFT 2026 Hackathon Entry**

---

## 📄 License

MIT License — See [LICENSE](LICENSE) for details.

---

<p align="center">
  <img src="https://img.shields.io/badge/Made_with-🧬_DNA-00e5c7?style=for-the-badge" />
</p>
