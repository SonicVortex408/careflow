import React, { useEffect, useState } from "react";
import { CheckCircle2, Loader2 } from "lucide-react";

import { COLORS } from "../../styles/tokens.js";
import { BRAIN_FOG_LEVELS, HAIR_LOSS_LEVELS, listSymptoms, submitSymptoms } from "../../services/symptomService.js";
import { Card } from "../../components/shared/Card.jsx";

const FOG_HELP = { never: "Never", rarely: "Rarely", sometimes: "Sometimes", often: "Often", always: "Nearly always" };
const HAIR_HELP = { none: "None", mild: "A little more than usual", moderate: "Clearly more than usual", severe: "A lot / visible thinning" };

function Choice({ name, options, labels, value, onChange }) {
  return (
    <div role="radiogroup" className="flex flex-wrap gap-2">
      {options.map((o) => (
        <label
          key={o}
          className="cursor-pointer rounded-xl border px-3 py-2 text-sm"
          style={{
            borderColor: value === o ? COLORS.teal : COLORS.line,
            backgroundColor: value === o ? COLORS.tealSoft : "white",
            color: value === o ? COLORS.teal : COLORS.ink,
          }}
        >
          <input type="radio" name={name} value={o} checked={value === o} onChange={() => onChange(o)} className="sr-only" />
          {labels[o]}
        </label>
      ))}
    </div>
  );
}

export function SymptomIntake({ onNavigate }) {
  const [fatigue, setFatigue] = useState(5);
  const [fog, setFog] = useState("");
  const [hair, setHair] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [history, setHistory] = useState([]);

  useEffect(() => { listSymptoms().then(setHistory).catch(() => {}); }, []);

  const submit = async (e) => {
    e.preventDefault();
    if (!fog || !hair) return setError("Please answer every question.");
    setSaving(true);
    setError("");
    try {
      const entry = await submitSymptoms({ fatigueSeverity: Number(fatigue), brainFogFrequency: fog, hairLoss: hair, notes });
      setHistory((h) => [entry, ...h]);
      setSaved(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-3xl mx-auto space-y-5">
      <header>
        <h1 className="text-2xl font-bold" style={{ color: COLORS.ink }}>How have you been feeling?</h1>
        <p className="text-sm mt-1" style={{ color: COLORS.slate }}>Think about the last two weeks. Your answers are added to your next lab report.</p>
      </header>

      <Card className="p-6">
        <form onSubmit={submit} className="space-y-6">
          <fieldset>
            <legend className="text-sm font-semibold mb-1" style={{ color: COLORS.ink }}>Tiredness</legend>
            <p className="text-xs mb-3" style={{ color: COLORS.slate }}>1 = none, 10 = the worst you can imagine</p>
            <div className="flex items-center gap-4">
              <input type="range" min={1} max={10} step={1} value={fatigue} onChange={(e) => setFatigue(e.target.value)}
                className="flex-1" style={{ accentColor: COLORS.teal }} aria-label="Tiredness from 1 to 10" />
              <output className="w-10 text-center text-xl font-bold tabular-nums" style={{ color: COLORS.ink }}>{fatigue}</output>
            </div>
          </fieldset>

          <fieldset>
            <legend className="text-sm font-semibold mb-2" style={{ color: COLORS.ink }}>Brain fog (trouble focusing or remembering)</legend>
            <Choice name="fog" options={BRAIN_FOG_LEVELS} labels={FOG_HELP} value={fog} onChange={setFog} />
          </fieldset>

          <fieldset>
            <legend className="text-sm font-semibold mb-2" style={{ color: COLORS.ink }}>Hair shedding or thinning (last 3 months)</legend>
            <Choice name="hair" options={HAIR_LOSS_LEVELS} labels={HAIR_HELP} value={hair} onChange={setHair} />
          </fieldset>

          <div>
            <label htmlFor="notes" className="block text-sm font-semibold mb-1" style={{ color: COLORS.ink }}>Anything else? (optional)</label>
            <textarea id="notes" rows={3} maxLength={2000} value={notes} onChange={(e) => setNotes(e.target.value)}
              className="w-full rounded-xl border px-3 py-2 text-sm" style={{ borderColor: COLORS.line }} />
          </div>

          {error && <p role="alert" className="text-sm" style={{ color: COLORS.critical }}>{error}</p>}
          {saved && (
            <p className="flex items-center gap-2 text-sm" style={{ color: COLORS.success }}>
              <CheckCircle2 className="w-4 h-4" /> Saved.{" "}
              <button type="button" className="font-semibold underline" onClick={() => onNavigate("upload")}>Upload a lab report</button>
            </p>
          )}

          <button type="submit" disabled={saving} className="inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60" style={{ backgroundColor: COLORS.teal }}>
            {saving && <Loader2 className="w-4 h-4 animate-spin" />} Save check-in
          </button>
        </form>
      </Card>

      {history.length > 0 && (
        <Card className="p-5">
          <h2 className="text-base font-semibold mb-3" style={{ color: COLORS.ink }}>Previous check-ins</h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs" style={{ color: COLORS.slate }}>
                <th className="py-1.5 font-medium">Date</th><th className="font-medium">Tiredness</th><th className="font-medium">Brain fog</th><th className="font-medium">Hair loss</th>
              </tr>
            </thead>
            <tbody>
              {history.slice(0, 10).map((h) => (
                <tr key={h.id} className="border-t" style={{ borderColor: COLORS.line, color: COLORS.ink }}>
                  <td className="py-2">{new Date(h.createdAt).toLocaleDateString()}</td>
                  <td className="tabular-nums">{h.fatigueSeverity}/10</td>
                  <td>{FOG_HELP[h.brainFogFrequency]}</td>
                  <td>{HAIR_HELP[h.hairLoss]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}

export default SymptomIntake;
