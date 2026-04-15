import type { CategoryBreakdown as Category } from "../api/types";

function scoreColor(score: number): string {
  if (score >= 75) return "#16a34a";
  if (score >= 50) return "#ca8a04";
  if (score >= 25) return "#ea580c";
  return "#dc2626";
}

export default function CategoryBreakdown({ category }: { category: Category }) {
  const pct = Math.round(category.score_0_100);
  const color = scoreColor(pct);
  return (
    <details className="category">
      <summary>
        <div className="category-head">
          <span className="category-name">{category.name.replace("_", " ")}</span>
          <span className="category-weight">weight {(category.weight * 100).toFixed(0)}%</span>
          <span className="category-score" style={{ color }}>{pct}/100</span>
        </div>
        <div className="bar">
          <div className="bar-fill" style={{ width: `${pct}%`, background: color }} />
        </div>
      </summary>
      <ul className="rule-list">
        {category.rules.map((r) => (
          <li key={r.name} className="rule">
            <div className="rule-label">
              <span>{r.label}</span>
              <span className="rule-score">
                {(r.normalized_score * 100).toFixed(0)}/100
              </span>
            </div>
            <div className="rule-bar">
              <div
                className="rule-bar-fill"
                style={{
                  width: `${r.normalized_score * 100}%`,
                  background: scoreColor(r.normalized_score * 100),
                }}
              />
            </div>
            <div className="rule-reason">{r.reason}</div>
          </li>
        ))}
      </ul>
    </details>
  );
}
