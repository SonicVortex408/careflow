export const getAdminProfile = async (req, res) => {
    res.json({
        success: true,
        admin: req.account,
    });
};