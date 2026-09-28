import React from "react";

export function AIAssistant() {
  return (
    <div
      style={{
        width: "100%",
        minHeight: "500px",
        backgroundColor: "white",
        border: "3px solid red",
        borderRadius: "16px",
        padding: "30px",
        marginTop: "30px",
      }}
    >
      <h1
        style={{
          fontSize: "30px",
          fontWeight: "bold",
          color: "black",
        }}
      >
        🤖 CAREFLOW AI
      </h1>

      <p
        style={{
          fontSize: "18px",
          color: "black",
          marginTop: "20px",
        }}
      >
        If you can see this box, AIAssistant is rendering correctly.
      </p>
    </div>
  );
}

export default AIAssistant;

