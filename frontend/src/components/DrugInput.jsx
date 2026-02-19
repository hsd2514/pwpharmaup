import { useState, useEffect, useMemo, useRef } from "react";
import { Pill, X, ChevronDown } from "lucide-react";

const FALLBACK_DRUGS = [
  { name: "CODEINE", gene: "CYP2D6", category: "Opioid Analgesic" },
  { name: "CLOPIDOGREL", gene: "CYP2C19", category: "Antiplatelet" },
  { name: "WARFARIN", gene: "CYP2C9", category: "Anticoagulant" },
  { name: "SIMVASTATIN", gene: "SLCO1B1", category: "Statin" },
  { name: "AZATHIOPRINE", gene: "TPMT", category: "Immunosuppressant" },
  { name: "FLUOROURACIL", gene: "DPYD", category: "Chemotherapy" },
];

const DRUG_META = {
  CODEINE: { gene: "CYP2D6", category: "Opioid Analgesic" },
  CLOPIDOGREL: { gene: "CYP2C19", category: "Antiplatelet" },
  WARFARIN: { gene: "CYP2C9", category: "Anticoagulant" },
  SIMVASTATIN: { gene: "SLCO1B1", category: "Statin" },
  AZATHIOPRINE: { gene: "TPMT", category: "Immunosuppressant" },
  FLUOROURACIL: { gene: "DPYD", category: "Chemotherapy" },
};

export default function DrugInput({ selectedDrugs, onDrugsChange, fetchDrugs }) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [supportedDrugs, setSupportedDrugs] = useState(FALLBACK_DRUGS);
  const dropdownRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
        setSearchTerm("");
      }
    }
    function handleEscape(event) {
      if (event.key === "Escape") {
        setIsOpen(false);
        setSearchTerm("");
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, []);

  useEffect(() => {
    let mounted = true;
    async function loadDrugs() {
      if (!fetchDrugs) return;
      try {
        const payload = await fetchDrugs();
        const names = payload?.drugs || [];
        if (!Array.isArray(names) || names.length === 0) return;
        const normalized = names
          .filter((n) => typeof n === "string")
          .map((name) => {
            const key = name.toUpperCase();
            const meta = DRUG_META[key] || { gene: "Unknown", category: "Pharmacotherapy" };
            return { name: key, gene: meta.gene, category: meta.category };
          });
        if (mounted) setSupportedDrugs(normalized);
      } catch {
        // Keep fallback list silently.
      }
    }
    loadDrugs();
    return () => {
      mounted = false;
    };
  }, [fetchDrugs]);

  const filteredDrugs = useMemo(
    () =>
      supportedDrugs.filter(
        (drug) =>
          drug.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          drug.category.toLowerCase().includes(searchTerm.toLowerCase()),
      ),
    [searchTerm, supportedDrugs],
  );

  const toggleDrug = (drugName) => {
    if (selectedDrugs.includes(drugName)) {
      onDrugsChange(selectedDrugs.filter((d) => d !== drugName));
    } else {
      onDrugsChange([...selectedDrugs, drugName]);
    }
  };

  const removeDrug = (drugName) => {
    onDrugsChange(selectedDrugs.filter((d) => d !== drugName));
  };

  return (
    <div className="space-y-4">
      {/* Selected drugs chips */}
      {selectedDrugs.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {selectedDrugs.map((drug) => {
            const drugInfo = supportedDrugs.find((d) => d.name === drug);
            return (
              <div
                key={drug}
                className="inline-flex items-center gap-2 rounded-md border border-cyan-glow/35 bg-cyan-glow/12 px-3 py-1.5"
              >
                <Pill className="w-3.5 h-3.5 text-cyan-glow" />
                <span className="text-sm font-semibold text-cyan-glow">{drug}</span>
                <span className="text-xs text-mist">{drugInfo?.gene}</span>
                <button
                  onClick={(event) => {
                    event.stopPropagation();
                    removeDrug(drug);
                  }}
                  className="ml-1 hover:text-danger transition-colors"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            );
          })}
        </div>
      )}

      {/* Dropdown */}
      <div ref={dropdownRef} className="relative z-30">
        <button
          type="button"
          onClick={() => {
            setIsOpen((open) => !open);
            if (isOpen) setSearchTerm("");
          }}
          className="w-full rounded-xl border border-ash/60 bg-slate/60 px-4 py-3 text-left transition-colors hover:border-cyan-glow/50"
        >
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <Pill className="w-5 h-5 text-cyan-glow" />
              <span className="text-light">
                {selectedDrugs.length === 0
                  ? "Select drugs to analyze"
                  : `${selectedDrugs.length} drug${selectedDrugs.length > 1 ? "s" : ""} selected`}
              </span>
            </div>
            <ChevronDown
              className={`w-5 h-5 text-mist transition-transform ${isOpen ? "rotate-180" : ""}`}
            />
          </div>
        </button>

        {isOpen && (
          <div className="absolute left-0 right-0 top-[calc(100%+0.5rem)] z-50 w-full overflow-hidden rounded-xl border border-ash/60 bg-abyss/98 shadow-[0_16px_44px_rgba(2,6,10,0.55)]">
            {/* Search input */}
            <div className="p-3 border-b border-ash/50">
              <input
                type="text"
                placeholder="Search drugs..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full px-3 py-2 bg-abyss/50 border border-ash/50 rounded-lg text-light placeholder-mist focus:outline-none focus:border-cyan-glow/50"
              />
            </div>

            {/* Drug list */}
            <div className="max-h-64 overflow-y-auto">
              {filteredDrugs.length === 0 && (
                <div className="px-4 py-5 text-sm text-mist">
                  No matching drugs found.
                </div>
              )}
              {filteredDrugs.map((drug) => {
                const isSelected = selectedDrugs.includes(drug.name);
                return (
                  <button
                    type="button"
                    key={drug.name}
                    onClick={() => toggleDrug(drug.name)}
                    className={`w-full flex items-center justify-between px-4 py-3 hover:bg-cyan-glow/5 transition-colors ${
                      isSelected ? "bg-cyan-glow/10" : ""
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-4 h-4 rounded border-2 flex items-center justify-center transition-colors ${
                          isSelected
                            ? "bg-cyan-glow border-cyan-glow"
                            : "border-ash"
                        }`}
                      >
                        {isSelected && (
                          <svg
                            className="w-2.5 h-2.5 text-void"
                            fill="currentColor"
                            viewBox="0 0 12 12"
                          >
                            <path d="M10.28 2.28L3.989 8.575 1.695 6.28A1 1 0 00.28 7.695l3 3a1 1 0 001.414 0l7-7A1 1 0 0010.28 2.28z" />
                          </svg>
                        )}
                      </div>
                      <div className="text-left">
                        <p className="font-medium text-light">{drug.name}</p>
                        <p className="text-xs text-mist">{drug.category}</p>
                      </div>
                    </div>
                    <span className="text-xs font-mono text-cyan-dim">
                      {drug.gene}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
