import React from "react";
import { COLORS } from "../../styles/tokens.js";
import { Card } from "../shared/Card.jsx";
import { DoctorStatusPill } from "../shared/Badges.jsx";

export function DoctorCard({ doctor }) {
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="text-sm font-semibold" style={{ color: COLORS.ink }}>{doctor.name}</h3>
          <p className="text-xs" style={{ color: COLORS.slate }}>{doctor.department} · {doctor.specialization}</p>
        </div>
        <DoctorStatusPill status={doctor.status} />
      </div>
      <div className="grid grid-cols-2 gap-3 text-sm mb-3">
        <div>
          <div className="text-xs" style={{ color: COLORS.slate }}>Current patient</div>
          <div className="font-medium" style={{ color: COLORS.ink }}>{doctor.currentPatient ? `#${doctor.currentPatient}` : "—"}</div>
        </div>
        <div>
          <div className="text-xs" style={{ color: COLORS.slate }}>Queue</div>
          <div className="font-medium" style={{ color: COLORS.ink }}>{doctor.queue} patients</div>
        </div>
        <div>
          <div className="text-xs" style={{ color: COLORS.slate }}>Next available</div>
          <div className="font-medium" style={{ color: COLORS.ink }}>{doctor.nextAvailable > 0 ? `~${doctor.nextAvailable} min` : "Now"}</div>
        </div>
        <div>
          <div className="text-xs" style={{ color: COLORS.slate }}>Consultation load</div>
          <div className="font-medium" style={{ color: COLORS.ink }}>{doctor.load}%</div>
        </div>
      </div>
      <div className="w-full h-1.5 rounded-full" style={{ backgroundColor: "#EEF2F1" }}>
        <div className="h-1.5 rounded-full" style={{ width: `${doctor.load}%`, backgroundColor: doctor.load >= 80 ? COLORS.critical : doctor.load >= 55 ? COLORS.warning : COLORS.success }} />
      </div>
    </Card>
  );
}

export default DoctorCard;
