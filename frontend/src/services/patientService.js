/* ============================================================================
   patientService — mock implementation, ready to swap for real HTTP calls
   ========================================================================== */
import { PATIENTS_BASE } from "../data/mockData.js";

export async function fetchPatients() {
  return Promise.resolve(PATIENTS_BASE);
}

export async function createPatient(patient) {
  // eslint-disable-next-line no-console
  console.log("createPatient (mock):", patient);
  return Promise.resolve(patient);
}

export async function updatePatient(id, updates) {
  // eslint-disable-next-line no-console
  console.log("updatePatient (mock):", id, updates);
  return Promise.resolve({ id, ...updates });
}
