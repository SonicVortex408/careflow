import { DOCTORS_BASE } from "../data/mockData.js";

export async function fetchDoctors() {
  return Promise.resolve(DOCTORS_BASE);
}

export async function updateDoctorStatus(id, status) {
  // eslint-disable-next-line no-console
  console.log("updateDoctorStatus (mock):", id, status);
  return Promise.resolve({ id, status });
}
