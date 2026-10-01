const express = require('express');
const router = express.Router();
const paperRoutes = require('./papers');
const projectRoutes = require('./projects');
const analyticsRoutes = require('./analytics');
const searchRoutes = require('./search');

router.use('/api/papers', paperRoutes);
router.use('/api/projects', projectRoutes);
router.use('/api/analytics', analyticsRoutes);
router.use('/api/search', searchRoutes);

module.exports = router;