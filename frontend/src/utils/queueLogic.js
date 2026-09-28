/* ============================================================================
   QUEUE LOGIC (prototype, deterministic)
   Prototype prioritization logic for demonstration purposes. It does not
   replace clinical triage or professional medical judgment.
   ========================================================================== */

export function workloadStatus(pct) {
  if (pct >= 80) return "Critical";
  if (pct >= 60) return "High";
  if (pct >= 35) return "Moderate";
  return "Low";
}

export const PRIORITY_WEIGHT = { Critical: 60, High: 42, Medium: 24, Low: 10 };

/**
 * Priority Score = Medical Priority + Waiting Time Score
 *                  + Appointment Factor + Resource Availability Factor
 */
export function priorityScore(patient, dept) {
  const urgency = PRIORITY_WEIGHT[patient.priority] ?? 10;
  const waitScore = Math.min(20, Math.round(patient.waitTime * 0.6));
  const apptFactor = patient.appointment === "Scheduled" ? 8 : 3;
  const deptWorkload = dept ? dept.workload : 50;
  const resourceFactor = Math.round((100 - deptWorkload) * 0.1);
  const total = Math.min(99, urgency + waitScore + apptFactor + resourceFactor);
  return { total, urgency, waitScore, apptFactor, resourceFactor };
}

export function predictWait(dept, queuePosition = 3) {
  const queueFactor = Math.round(queuePosition * 1.3);
  const doctorFactor = dept ? -Math.round(dept.doctorsAvailable * 2.5) : -3;
  const loadFactor = dept ? Math.round(dept.workload * 0.14) : 8;
  const priorityFactor = 6;
  const base = Math.max(3, queueFactor + doctorFactor + loadFactor + priorityFactor);
  const confidence = Math.max(62, 96 - Math.round((dept?.workload || 40) * 0.25));
  return { estimate: base, confidence, queueFactor, doctorFactor, loadFactor, priorityFactor };
}
