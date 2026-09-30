import React from "react";
import { COLORS } from "../../styles/tokens.js";

export function Card({ children, className = "", style, ...rest }) {
  return (
    <div
      className={`bg-white rounded-2xl border shadow-sm ${className}`}
      style={{ borderColor: COLORS.line, ...style }}
      {...rest}
    >
      {children}
    </div>
  );
}

export default Card;
