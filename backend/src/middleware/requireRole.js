const requireRole = (...roles) => (req, res, next) => {
    if (!roles.includes(req.role)) {
        return res.status(403).json({
            success: false,
            message: `Requires role: ${roles.join(" or ")}`,
        });
    }

    next();
};

export default requireRole;
