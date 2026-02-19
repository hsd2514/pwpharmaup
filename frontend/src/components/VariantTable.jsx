import { Dna } from "lucide-react";

export default function VariantTable({ variants }) {
  if (!variants || variants.length === 0) {
    return (
      <div className="glass-panel p-8 text-center">
        <Dna className="w-12 h-12 text-ash mx-auto mb-4" />
        <p className="text-mist">No variants detected in target genes</p>
        <p className="text-xs text-ash mt-2">
          Assuming wild-type (*1/*1) for all genes
        </p>
      </div>
    );
  }

  return (
    <div className="glass-panel overflow-hidden">
      <div className="p-4 border-b border-ash/30">
        <h3 className="text-lg font-semibold text-light font-[Syne]">
          Detected Variants
        </h3>
        <p className="text-sm text-mist mt-1">
          {variants.length} variant{variants.length !== 1 ? "s" : ""} identified
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-cyan-glow/5">
              <th className="px-4 py-3 text-left text-xs font-bold text-cyan-glow uppercase tracking-wider">
                rsID
              </th>
              <th className="px-4 py-3 text-left text-xs font-bold text-cyan-glow uppercase tracking-wider">
                Gene
              </th>
              <th className="px-4 py-3 text-left text-xs font-bold text-cyan-glow uppercase tracking-wider">
                Star Allele
              </th>
              <th className="px-4 py-3 text-left text-xs font-bold text-cyan-glow uppercase tracking-wider">
                Zygosity
              </th>
              <th className="px-4 py-3 text-left text-xs font-bold text-cyan-glow uppercase tracking-wider">
                Function
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-ash/30">
            {variants.map((variant, index) => (
              <tr
                key={`${variant.rsid}-${index}`}
                className="hover:bg-cyan-glow/5 transition-colors"
              >
                <td className="px-4 py-3">
                  <span className="font-mono text-sm text-light">
                    {variant.rsid}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className="font-mono text-sm text-cyan-glow font-semibold">
                    {variant.gene}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className="font-mono text-sm text-light">
                    {variant.star_allele}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${
                      variant.zygosity === "homozygous"
                        ? "bg-amber-500/20 text-amber-400"
                        : "bg-cyan-glow/20 text-cyan-glow"
                    }`}
                  >
                    {variant.zygosity}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className="text-sm text-cloud">
                    {variant.function || variant.clinical_significance || "—"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
