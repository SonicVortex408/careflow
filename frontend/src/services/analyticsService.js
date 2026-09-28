import { WAIT_TREND, FLOW_STAGES } from "../data/mockData.js";

export async function fetchWaitTrend() {
  return Promise.resolve(WAIT_TREND);
}

export async function fetchPatientFlow() {
  return Promise.resolve(FLOW_STAGES);
}
