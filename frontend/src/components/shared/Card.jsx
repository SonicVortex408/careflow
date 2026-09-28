import React from "react";
import { COLORS } from "../../styles/tokens.js";

export function Card({ children, className = "", ...rest }) {
  return (
    <div
      className={`bg-white rounded-2xl border shadow-sm ${className}`}
      style={{ borderColor: COLORS.line }}
      {...rest}
    >
      {children}
    </div>
  );
}

export default Card;
