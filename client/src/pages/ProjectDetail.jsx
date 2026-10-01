import React, { useEffect, useState } from 'react';
import { useParams, useQuery } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { projectsApi } from '../services/api';
import { Card } from '../components/ui';

const ProjectDetail = () => {
  const { id } = useParams();
  const { data: project, isLoading, isError } = useQuery({
    queryKey: ['project', id],
    queryFn: () => projectsApi.getById(id),
    enabled: !!id,
  });

  if (!project && isLoading) return <div>Loading project...</div>;
  if (isError) return <div>Error loading project</div>;

  return (
    <section className="project-detail-section">
      <div className="project-detail-container">
        <header className="project-header">
          <h1>{project?.title || 'Project Detail'}</h1>
          <div className="project-meta-info">
            <span>Difficulty: {project?.difficulty}</span>
            <span>Category: {project?.category || 'General'}</span>
          </div>
        </header>

        <div className="project-content">
          <p className="project-description">
            {project?.description || 'No description available'}
          </p>

          {project?.technologies?.map((tech, index) => (
            <span key={index} className="tech-badge">
              {tech}
            </span>
          ))}

          <div className "project-stats">
            <span>⭐ {project?.stars || 0} Stars</span>
            <span>🍴 {project?.forks || 0} Forks</span>
          </div>
        </div>

        <div className="project-actions">
          <a href={project?.githubUrl} target="_blank" rel="noopener noreferrer" className="btn btn-primary">
            View on GitHub
          </a>
          <a href={project?.documentationUrl} target="_blank" rel="noopener noreferrer" className="btn btn-secondary">
            Read Documentation
          </a>
        </div>

        <h3>Related Projects</h3>
        <div className="projects-grid-small">
          {/* Related projects would be fetched here */}
          <p>No related projects found</p>
        </div>
      </div>
    </section>
  );
};

export default ProjectDetail;