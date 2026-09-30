import jwt from "jsonwebtoken";
import env from "../config/env.js";

const generateToken = (id, role) => {
    return jwt.sign(
        {
            id,
            role,
        },
        env.jwtSecret,
        {
            expiresIn: "7d",
        }
    );
};

export default generateToken;
