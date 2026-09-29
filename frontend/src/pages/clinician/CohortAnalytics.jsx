import React, { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Loader2 } from "lucide-react";

import { COLORS, VIZ } from "../../styles/tokens.js";
import { getInsight } from "../../services/insightService.js";
import { BIOMARKER_ORDER, formatValue } from "../../utils/biomarkers.js";
import { Card } from "../../components/shared/Card.jsx";
import { SyntheticDataNotice } from "../../components/shared/Badges.jsx";
import { ChartCard } from "../../components/analytics/ChartCard.jsx";
import { CohortScatter } from "../../components/biomarkers/CohortScatter.jsx";

// Right-skewed markers are easier to read on a log axis (matches the model's log transform).
const LOG_AXIS = new Set(["TSH", "TPOAB", "VITD", "B12", "FERRITIN"]);
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

const TARGET_LABEL = { fatigue: "Strong tiredness", brain_fog: "Frequent brain fog", hair_loss: "Noticeable hair loss" };

function Stat({ label, value, hint }) {
  return (
    <Card className="p-4">
      <div className="text-xs" style={{ color: COLORS.slate }}>{label}</div>
      <div className="text-2xl font-bold tabular-nums mt-1" style={{ color: COLORS.ink }}>{value}</div>
      {hint && <div className="text-xs mt-0.5" style={{ color: COLORS.slate }}>{hint}</div>}
    </Card>
  );
}

function ChartTip({ active, payload, render }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl border bg-white shadow p-2.5 text-xs" style={{ borderColor: COLORS.line, color: COLORS.ink }}>
      {render(payload[0].payload)}
    </div>
  );
}

export function CohortAnalytics() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [marker, setMarker] = useState("FERRITIN");
  const [target, setTarget] = useState("fatigue");

  useEffect(() => {
    Promise.all([getInsight("model"), getInsight("bands"), getInsight("cohort"), getInsight("catalog")])
      .then(([model, bands, cohort, catalog]) => setData({ model, bands, cohort, catalog }))
      .catch((e) => setError(e.message));
  }, []);

  const clusterRows = useMemo(
    () => (data?.cohort?.profiles || [])
      .map((p) => ({ name: p.name, rate: Math.round(p.fatigue_rate * 1000) / 10, size: p.size, share: p.share }))
      .sort((a, b) => b.rate - a.rate),
    [data]
  );

  if (error) return <p role="alert" className="p-8 text-sm" style={{ color: COLORS.critical }}>{error}</p>;
  if (!data) return <div className="p-8"><Loader2 className="w-5 h-5 animate-spin" style={{ color: COLORS.slate }} /></div>;

  const metrics = data.model.metrics;
  const band = data.bands.bands[marker];
  const unit = band.unit;
  const display = data.catalog.biomarkers[marker].display;
  const curve = band.risk_curve.map((p) => ({ value: p.value, risk: Math.round(p.risk * 1000) / 10 }));
  const xMin = curve[0].value;
  const xMax = curve.at(-1).value;
  const logAxis = LOG_AXIS.has(marker) && xMin > 0;
  const importance = Object.entries(metrics.global_importance[target])
    .filter(([k]) => !["age", "sex"].includes(k))
    .map(([k, v]) => ({ name: data.catalog.biomarkers[k]?.display || k, value: Math.round(v * 1000) / 1000 }))
    .sort((a, b) => b.value - a.value);

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-5">
      <header>
        <h1 className="text-2xl font-bold" style={{ color: COLORS.ink }}>Cohort analytics</h1>
        <p className="text-sm mt-1" style={{ color: COLORS.slate }}>
          Model version {data.model.semver} · seed {data.model.seed} · trained {new Date(data.model.created_at).toLocaleDateString()}
        </p>
      </header>

      <SyntheticDataNotice />

      <div className="grid gap-4 grid-cols-2 lg:grid-cols-5">
        {Object.entries(metrics.risk).map(([t, m]) => (
          <Stat key={t} label={`${TARGET_LABEL[t]} AUROC`} value={m.auroc.toFixed(2)} hint={`ECE ${m.ece_calibrated.toFixed(3)} · prevalence ${Math.round(m.prevalence * 100)}%`} />
        ))}
        <Stat label="K-Means groups" value={metrics.clustering.kmeans_k} hint={`silhouette ${metrics.clustering.kmeans_silhouette.toFixed(2)}`} />
        <Stat label="DBSCAN noise" value={`${Math.round(metrics.clustering.dbscan_noise_fraction * 100)}%`} hint={`GMM components ${metrics.clustering.gmm_components}`} />
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <Card className="p-5">
          <div className="flex flex-wrap items-center justify-between gap-2 mb-1">
            <h3 className="text-sm font-semibold" style={{ color: COLORS.ink }}>Tiredness risk across {display}</h3>
            <select value={marker} onChange={(e) => setMarker(e.target.value)} className="rounded-lg border px-2 py-1 text-sm" style={{ borderColor: COLORS.line }} aria-label="Marker">
              {BIOMARKER_ORDER.map((k) => <option key={k} value={k}>{data.catalog.biomarkers[k].display}</option>)}
            </select>
          </div>
          <p className="text-xs mb-3" style={{ color: COLORS.slate }}>
            Adjusted risk curve (spline logistic, age &amp; sex). Shaded: lab range. Outlined: discovered functional band
            {band.functional ? ` ${formatValue(band.functional.low)}–${formatValue(band.functional.high)} ${unit}` : " (none: curve too flat)"}.
          </p>
          <div style={{ width: "100%", height: 260 }}>
            <ResponsiveContainer>
              <LineChart data={curve} margin={{ top: 8, right: 16, bottom: 20, left: 0 }}>
                <CartesianGrid stroke={VIZ.grid} strokeDasharray="3 3" />
                <XAxis dataKey="value" type="number" domain={[xMin, xMax]} scale={logAxis ? "log" : "auto"} allowDataOverflow tickFormatter={formatValue} tick={{ fontSize: 10, fill: VIZ.axis }}
                  label={{ value: logAxis ? `${unit} (log scale)` : unit, position: "insideBottom", offset: -10, fontSize: 11, fill: VIZ.axis }} />
                <YAxis unit="%" tick={{ fontSize: 10, fill: VIZ.axis }} width={40} />
                <ReferenceArea x1={clamp(band.reference.low, xMin, xMax)} x2={clamp(band.reference.high, xMin, xMax)} fill={VIZ.referenceBand} fillOpacity={0.6} ifOverflow="hidden" />
                {band.functional && (
                  <ReferenceArea x1={clamp(band.functional.low, xMin, xMax)} x2={clamp(band.functional.high, xMin, xMax)} fill="none" stroke={VIZ.functionalBand} strokeWidth={1.5} strokeDasharray="4 3" ifOverflow="hidden" />
                )}
                <Tooltip content={<ChartTip render={(p) => <>{formatValue(p.value)} {unit}: <strong>{p.risk}%</strong> predicted risk</>} />} />
                <Line type="monotone" dataKey="risk" stroke={VIZ.series1} strokeWidth={2} dot={false} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <ChartCard title="Strong tiredness by cohort group" subtitle="Share of each K-Means group reporting fatigue ≥ 7/10">
          <ResponsiveContainer>
            <BarChart data={clusterRows} layout="vertical" margin={{ top: 0, right: 24, bottom: 0, left: 8 }} barCategoryGap={2}>
              <CartesianGrid horizontal={false} stroke={VIZ.grid} />
              <XAxis type="number" unit="%" tick={{ fontSize: 10, fill: VIZ.axis }} />
              <YAxis type="category" dataKey="name" width={150} tick={{ fontSize: 10, fill: VIZ.axis }} />
              <Tooltip cursor={{ fill: "#0000000a" }} content={<ChartTip render={(p) => <><strong>{p.name}</strong><div>{p.rate}% report strong tiredness</div><div>{p.size.toLocaleString()} people ({Math.round(p.share * 100)}%)</div></>} />} />
              <Bar dataKey="rate" fill={VIZ.series1} radius={[0, 4, 4, 0]} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <Card className="p-5">
          <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
            <h3 className="text-sm font-semibold" style={{ color: COLORS.ink }}>Global SHAP importance</h3>
            <select value={target} onChange={(e) => setTarget(e.target.value)} className="rounded-lg border px-2 py-1 text-sm" style={{ borderColor: COLORS.line }} aria-label="Symptom">
              {Object.keys(TARGET_LABEL).map((t) => <option key={t} value={t}>{TARGET_LABEL[t]}</option>)}
            </select>
          </div>
          <div style={{ width: "100%", height: 260 }}>
            <ResponsiveContainer>
              <BarChart data={importance} layout="vertical" margin={{ top: 0, right: 24, bottom: 0, left: 8 }} barCategoryGap={2}>
                <CartesianGrid horizontal={false} stroke={VIZ.grid} />
                <XAxis type="number" tick={{ fontSize: 10, fill: VIZ.axis }} />
                <YAxis type="category" dataKey="name" width={110} tick={{ fontSize: 10, fill: VIZ.axis }} />
                <Tooltip cursor={{ fill: "#0000000a" }} content={<ChartTip render={(p) => <><strong>{p.name}</strong><div>mean |SHAP| {p.value} (log-odds)</div></>} />} />
                <Bar dataKey="value" fill={VIZ.series1} radius={[0, 4, 4, 0]} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card className="p-5">
          <h3 className="text-sm font-semibold mb-3" style={{ color: COLORS.ink }}>Cohort map (PCA of 9-marker vectors)</h3>
          <CohortScatter cohort={data.cohort} height={280} />
        </Card>
      </div>
    </div>
  );
}

export default CohortAnalytics;
