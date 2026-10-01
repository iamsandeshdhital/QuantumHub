import React, { useEffect, useState } from 'react';
import { useParams, useQuery } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { projectsApi } from '../services/api';
import { Card } from '../components/ui';

const ProjectsList = () => {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['all-projects'],
    queryFn: () => projectsApi.getAll({ limit: 20 }),
    staleTime: 60000,
  });

  if (isLoading) return <div>Loading projects...</div>;
  if (isError) return <div>Error loading projects</div>;

  return (
    <section className="projects-section">
      <header className="section-header">
        <h2>Quantum Computing Projects</h2>
        <span className="project-count">
          {data?.projects?.length} projects found
        </span>
      </header>

      <div className="projects-grid">
        {data?.projects?.map((project) => (
          <article key={project.id} className="project-card">
            <div className="project-header">
              <h3 className="project-title">
                <a href={`/projects/${project.id}`}>{project.title}</a>
              </h3>
              <span className="project-type-badge">{project.type}</span>
            </div>
            <p className="project-description">
              {project.description || 'No description available'}
            </p>
            <div className="project-meta">
              <span>Difficulty: {project.difficulty}</span>
              <span>Category: {project.category || 'General'}</span>
            </div>
            <a href={`/projects/${project.id}`} className="project-link-view">View Details</a>
          </article>
        ))}
      </div>

      {data?.projects.length === 0 && (
        <p className="empty-state">No projects found. Check filters or add new projects.</p>
      )}
    </section>
  );
};

export default ProjectsList;