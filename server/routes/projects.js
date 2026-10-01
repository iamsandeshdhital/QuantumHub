const express = require('express');
const router = express.Router();
const { getDB } = require('../config/database');
const { AppError } = require('../middleware/errorHandler');

// GET /api/projects - Get all projects with filtering
router.get('/', async (req, res, next) => {
  try {
    const db = getDB();
    const projects = await db.getAllProjects(req.query);
    
    res.status(200).json({
      status: 'success',
      data: { projects }
    });
  } catch (error) {
    next(error);
  }
});

// GET /api/projects/:id - Get a single project by ID
router.get('/:id', async (req, res, next) => {
  try {
    const db = getDB();
    const project = await db.getProjectById(req.params.id);
    
    if (!project) {
      throw new AppError('Project not found', 404);
    }
    
    res.status(200).json({
      status: 'success',
      data: { project }
    });
  } catch (error) {
    next(error);
  }
});

module.exports = router;