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
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
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
| `GET`  | `/supported-drugs`       | List available drugs |
| `GET`  | `/normalize-drug/{drug}` | Normalize drug name  |
| `GET`  | `/sample-vcf/{filename}` | Download sample VCF  |
| `GET`  | `/health`                | Health check         |

### Example Request

```bash
curl -X POST http://localhost:8000/analyze \
  -F "vcf_file=@sample_vcf/pm_cyp2d6.vcf" \
  -F "drugs=codeine" \
  -F "drugs=tramadol"
```

---

## 🎨 Frontend Design

The UI follows a **biotech laboratory aesthetic**:

- **Color Palette:** Void black (#030608) + Bioluminescent cyan (#00e5c7)
- **Typography:** Syne (display), DM Sans (body), JetBrains Mono (data)
- **Effects:** Glass panels, molecular grid background, subtle glow effects
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

## 📋 Supported Genes & Drugs

### Genes

- **CYP2D6** — codeine, tramadol, tamoxifen
- **CYP2C19** — clopidogrel, omeprazole, escitalopram
- **CYP2C9** — warfarin, phenytoin
- **DPYD** — fluorouracil, capecitabine
- **TPMT** — azathioprine, mercaptopurine
- **SLCO1B1** — simvastatin
- **UGT1A1** — irinotecan

### Risk Levels

- 🟢 **Low** — Standard dosing, no adjustments needed
- 🟡 **Moderate** — Minor adjustments, routine monitoring
- 🟠 **High** — Significant adjustments, enhanced monitoring
- 🔴 **Critical** — Avoid drug or use alternative therapy

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
