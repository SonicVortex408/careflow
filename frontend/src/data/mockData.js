export const DEPARTMENTS_BASE = [
  { id: "emergency", name: "Emergency", queue: 24, doctorsTotal: 6, doctorsAvailable: 2, waitTime: 18, workload: 88 },
  { id: "cardiology", name: "Cardiology", queue: 14, doctorsTotal: 5, doctorsAvailable: 1, waitTime: 27, workload: 82 },
  { id: "orthopedics", name: "Orthopedics", queue: 9, doctorsTotal: 4, doctorsAvailable: 2, waitTime: 21, workload: 58 },
  { id: "pediatrics", name: "Pediatrics", queue: 11, doctorsTotal: 4, doctorsAvailable: 2, waitTime: 15, workload: 51 },
  { id: "neurology", name: "Neurology", queue: 6, doctorsTotal: 3, doctorsAvailable: 2, waitTime: 12, workload: 39 },
  { id: "general", name: "General Medicine", queue: 5, doctorsTotal: 4, doctorsAvailable: 3, waitTime: 9, workload: 28 },
  { id: "radiology", name: "Radiology", queue: 3, doctorsTotal: 2, doctorsAvailable: 2, waitTime: 7, workload: 22 },
];

export const DOCTORS_BASE = [
  { id: "D01", name: "Dr. Ananya Mehta", department: "Cardiology", specialization: "Interventional Cardiology", status: "Consulting", currentPatient: "P1024", queue: 7, nextAvailable: 18, load: 84 },
  { id: "D02", name: "Dr. Rohan Kapoor", department: "Emergency", specialization: "Emergency Medicine", status: "Consulting", currentPatient: "P1031", queue: 9, nextAvailable: 6, load: 91 },
  { id: "D03", name: "Dr. Sana Iqbal", department: "Emergency", specialization: "Trauma Surgery", status: "Available", currentPatient: null, queue: 0, nextAvailable: 0, load: 12 },
  { id: "D04", name: "Dr. Vikram Nair", department: "Orthopedics", specialization: "Sports Medicine", status: "Consulting", currentPatient: "P1029", queue: 4, nextAvailable: 14, load: 63 },
  { id: "D05", name: "Dr. Priya Desai", department: "Orthopedics", specialization: "Joint Replacement", status: "Available", currentPatient: null, queue: 1, nextAvailable: 0, load: 20 },
  { id: "D06", name: "Dr. Arjun Reddy", department: "Pediatrics", specialization: "General Pediatrics", status: "Consulting", currentPatient: "P1033", queue: 3, nextAvailable: 11, load: 55 },
  { id: "D07", name: "Dr. Neha Kulkarni", department: "Pediatrics", specialization: "Neonatology", status: "On Break", currentPatient: null, queue: 2, nextAvailable: 9, load: 40 },
  { id: "D08", name: "Dr. Farhan Ali", department: "Neurology", specialization: "Stroke Care", status: "Available", currentPatient: null, queue: 1, nextAvailable: 0, load: 25 },
  { id: "D09", name: "Dr. Meera Pillai", department: "General Medicine", specialization: "Internal Medicine", status: "Available", currentPatient: null, queue: 0, nextAvailable: 0, load: 15 },
  { id: "D10", name: "Dr. Karan Malhotra", department: "General Medicine", specialization: "Family Medicine", status: "Consulting", currentPatient: "P1040", queue: 2, nextAvailable: 8, load: 34 },
  { id: "D11", name: "Dr. Ishita Rao", department: "Radiology", specialization: "Diagnostic Imaging", status: "Consulting", currentPatient: "P1037", queue: 1, nextAvailable: 5, load: 30 },
  { id: "D12", name: "Dr. Aditya Bose", department: "Cardiology", specialization: "Electrophysiology", status: "Unavailable", currentPatient: null, queue: 0, nextAvailable: 45, load: 0 },
];

export const SYMPTOMS = {
  Emergency: "Chest pain, shortness of breath",
  Cardiology: "Irregular heartbeat, fatigue",
  Orthopedics: "Knee pain following fall",
  Pediatrics: "Fever, mild cough",
  Neurology: "Recurrent headaches, dizziness",
  "General Medicine": "Fatigue, routine check-up",
  Radiology: "Follow-up imaging required",
};

export function subMin(hhmm, mins) {
  const [time, mer] = hhmm.split(" ");
  let [h, m] = time.split(":").map(Number);
  if (mer === "PM" && h !== 12) h += 12;
  if (mer === "AM" && h === 12) h = 0;
  let total = h * 60 + m + mins;
  total = ((total % 1440) + 1440) % 1440;
  let hh = Math.floor(total / 60);
  const mm = total % 60;
  const outMer = hh >= 12 ? "PM" : "AM";
  hh = hh % 12; if (hh === 0) hh = 12;
  return `${hh}:${String(mm).padStart(2, "0")} ${outMer}`;
}

const PATIENTS_RAW = [
  { id: "P1024", name: "Rahul Sharma", age: 48, department: "Cardiology", priority: "Critical", appointment: "Walk-in", arrivalTime: "10:24 AM", waitTime: 4, doctor: "Dr. Ananya Mehta", status: "Being evaluated" },
  { id: "P1031", name: "Ayesha Khan", age: 34, department: "Emergency", priority: "Critical", appointment: "Walk-in", arrivalTime: "10:41 AM", waitTime: 2, doctor: "Dr. Rohan Kapoor", status: "Being evaluated" },
  { id: "P1027", name: "Vivaan Joshi", age: 61, department: "Emergency", priority: "High", appointment: "Walk-in", arrivalTime: "10:12 AM", waitTime: 15, doctor: "Unassigned", status: "Waiting" },
  { id: "P1029", name: "Meenal Kulkarni", age: 29, department: "Orthopedics", priority: "High", appointment: "Scheduled", arrivalTime: "10:05 AM", waitTime: 14, doctor: "Dr. Vikram Nair", status: "Being evaluated" },
  { id: "P1032", name: "Kabir Singh", age: 8, department: "Pediatrics", priority: "Medium", appointment: "Scheduled", arrivalTime: "10:31 AM", waitTime: 22, doctor: "Unassigned", status: "Waiting" },
  { id: "P1033", name: "Ira Bhatt", age: 5, department: "Pediatrics", priority: "Medium", appointment: "Walk-in", arrivalTime: "10:20 AM", waitTime: 9, doctor: "Dr. Arjun Reddy", status: "Being evaluated" },
  { id: "P1035", name: "Devansh Rao", age: 55, department: "Neurology", priority: "High", appointment: "Scheduled", arrivalTime: "10:02 AM", waitTime: 31, doctor: "Unassigned", status: "Waiting" },
  { id: "P1037", name: "Sara Fernandes", age: 40, department: "Radiology", priority: "Low", appointment: "Scheduled", arrivalTime: "10:15 AM", waitTime: 5, doctor: "Dr. Ishita Rao", status: "Being evaluated" },
  { id: "P1040", name: "Aarav Menon", age: 37, department: "General Medicine", priority: "Low", appointment: "Walk-in", arrivalTime: "10:38 AM", waitTime: 8, doctor: "Dr. Karan Malhotra", status: "Being evaluated" },
  { id: "P1042", name: "Naina Chatterjee", age: 66, department: "Cardiology", priority: "High", appointment: "Walk-in", arrivalTime: "10:44 AM", waitTime: 19, doctor: "Unassigned", status: "Waiting" },
  { id: "P1044", name: "Reyansh Iyer", age: 22, department: "Orthopedics", priority: "Low", appointment: "Scheduled", arrivalTime: "10:29 AM", waitTime: 12, doctor: "Unassigned", status: "Waiting" },
  { id: "P1046", name: "Diya Bhatt", age: 44, department: "Emergency", priority: "Medium", appointment: "Walk-in", arrivalTime: "10:47 AM", waitTime: 6, doctor: "Unassigned", status: "Waiting" },
  { id: "P1048", name: "Yusuf Ansari", age: 71, department: "Neurology", priority: "Critical", appointment: "Walk-in", arrivalTime: "10:49 AM", waitTime: 1, doctor: "Unassigned", status: "Waiting" },
  { id: "P1050", name: "Ananya Ghosh", age: 30, department: "General Medicine", priority: "Low", appointment: "Scheduled", arrivalTime: "10:33 AM", waitTime: 16, doctor: "Unassigned", status: "Waiting" },
];

export const PATIENTS_BASE = PATIENTS_RAW.map((p) => ({
  ...p,
  timeline: [
    { time: subMin(p.arrivalTime, 0), label: "Patient registered" },
    { time: subMin(p.arrivalTime, -3), label: "Triage completed" },
    { time: subMin(p.arrivalTime, -6), label: `Added to ${p.department} queue` },
    ...(p.doctor !== "Unassigned" ? [{ time: subMin(p.arrivalTime, -(6 + p.waitTime)), label: `${p.doctor} assigned` }] : []),
    ...(p.status === "Being evaluated" ? [{ time: subMin(p.arrivalTime, -(9 + p.waitTime)), label: "Consultation started" }] : []),
  ],
}));

export const WAIT_TREND = [
  { time: "8 AM", wait: 14 }, { time: "9 AM", wait: 18 }, { time: "10 AM", wait: 26 },
  { time: "11 AM", wait: 31 }, { time: "12 PM", wait: 24 }, { time: "1 PM", wait: 19 },
  { time: "2 PM", wait: 22 }, { time: "3 PM", wait: 27 },
];

export const FLOW_STAGES = [
  { stage: "Registered", count: 186 }, { stage: "Triaged", count: 172 },
  { stage: "Waiting", count: 96 }, { stage: "Consulting", count: 41 }, { stage: "Completed", count: 128 },
];

export const ALERTS_BASE = [
  { id: "A1", type: "queue", severity: "critical", title: "High Queue Alert", message: "Emergency department has exceeded the recommended queue threshold.", status: "active" },
  { id: "A2", type: "resource", severity: "warning", title: "Resource Alert", message: "Cardiology has 8 patients waiting and only 2 available doctors.", status: "active" },
  { id: "A3", type: "wait", severity: "warning", title: "Waiting Time Alert", message: "Average waiting time in Orthopedics has increased by 18%.", status: "active" },
  { id: "A4", type: "recommendation", severity: "info", title: "CareFlow Recommendation", message: "Consider assigning an available doctor from General Medicine to assist with Cardiology's current workload.", status: "active" },
  { id: "A5", type: "resource", severity: "info", title: "Doctor Available", message: "Dr. Farhan Ali (Neurology) is now available for new patients.", status: "resolved" },
];

export const NOTIFICATIONS_BASE = [
  { id: "N1", text: "Emergency queue increased to 24 patients.", time: "2 min ago", read: false },
  { id: "N2", text: "Dr. Mehta is now available.", time: "6 min ago", read: false },
  { id: "N3", text: "Cardiology predicted waiting time increased to 32 minutes.", time: "11 min ago", read: false },
  { id: "N4", text: "Patient #P1024 requires priority attention.", time: "14 min ago", read: true },
];
