import { DEPARTMENTS_BASE } from "../data/mockData.js";
import { priorityScore, predictWait } from "../utils/queueLogic.js";

export async function fetchDepartments() {
  return Promise.resolve(DEPARTMENTS_BASE);
}

export async function getPriorityScore(patient, dept) {
  return Promise.resolve(priorityScore(patient, dept));
}

export async function getPredictedWait(dept, queuePosition) {
  return Promise.resolve(predictWait(dept, queuePosition));
}
