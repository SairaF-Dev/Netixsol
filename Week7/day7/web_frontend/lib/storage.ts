import type { SessionAppointment } from "@/types/api";

const APPOINTMENTS_KEY = "sara_session_appointments";

export const storage = {
  loadAppointments(): SessionAppointment[] { try { return JSON.parse(localStorage.getItem(APPOINTMENTS_KEY) || "[]"); } catch { return []; } },
  saveAppointments(items: SessionAppointment[]) { localStorage.setItem(APPOINTMENTS_KEY, JSON.stringify(items)); },
  clearAppointments() { localStorage.removeItem(APPOINTMENTS_KEY); },
};
