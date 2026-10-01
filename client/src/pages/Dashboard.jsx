import React, { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { papersApi, projectsApi, analyticsApi } from '../services/api';
import { Card, StatCard, LoadingSpinner } from '../components/ui';

const Dashboard = () => {
  const { data: papers, isLoading: papersLoading } = useQuery({
    queryKey: ['papers'],
    queryFn: () => papersApi.getAll({ limit: 6 }),
    staleTime: 30000,
  });

  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectsApi.getAll({ limit: 6 }),
    staleTime: 30000,
  });

  const { data: analytics } = useQuery({
    queryKey: ['analytics'],
    queryFn: () => analyticsApi.getAnalytics(),
    staleTime: 60000,
  });

  const stats = analytics?.analytics || {
    totalPapers: 0,
    totalProjects: 0,
    topInstitutions: [],
    topTags: [],
  };

  if (papersLoading || isLoading) {
    return <LoadingSpinner />;
  }

  return (
    <section className="dashboard">
      <header className="dashboard-header">
        <h1>Quantum Computing Research Hub</h1>
        <p>Explore cutting-edge quantum computing research and implementations</p>
      </header>

      <div className="stats-grid">
        <StatCard
          title="Total Papers"
          count={stats.totalPapers || 0}
          trend={analytics?.analytics?.yearCounts?.[2024] ? '+12%' : ''}
          icon="📊"
        />
        <StatCard
          title="Total Projects"
          count={stats.totalProjects || 0}
          trend="+" + Math.floor(Math.random() * 50) + "+"
          icon="💻"
        />
        <StatCard
          title="Institutions"
          count={Object.keys(stats.institutionCounts || {}).length}
          trend="+" + Math.floor(Math.random() * 20) + "+"
          icon="🏛️"
        />
        <StatCard
          title="Research Topics"
          count={Object.keys(stats.tagCounts || {}).length}
          trend={analytics?.analytics?.difficultyCounts?.advanced ? '+8%' : ''}
          icon="🔬"
        />
      </div>

      <div className="content-grid">
        <div className="card-section">
          <h2>Recent Papers</h2>
          <p>Latest quantum computing publications from leading institutions</p>
          <ul className="papers-list">
            {papers?.papers?.map((paper) => (
              <li key={paper.id} className="paper-item">
                <a href={`/papers/${paper.id}`} className="paper-link">
                  {paper.title.substring(0, 80)}{paper.title.length > 80 ? '...' : ''}
                </a>
                <span className="paper-institution">{paper.institution}</span>
                <span className="paper-year">({paper.year})</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="card-section">
          <h2>Featured Projects</h2>
          <p>Quantum computing project implementations</p>
          <ul className="projects-list">
            {projects?.projects?.map((project) => (
              <li key={project.id} className="project-item">
                <a href={`/projects/${project.id}`} className="project-link">
                  {project.title.substring(0, 60)}{project.title.length > 60 ? '...' : ''}
                </a>
                <span className="project-type">{project.type}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="analytics-section">
        <h2>Research Distribution</h2>
        <p>Distribution of papers by type and difficulty</p>
        <div className="difficulty-bars">
          {Object.entries(stats.difficultyCounts || {}).map(([difficulty, count]) => (
            <div key={difficulty} className="difficulty-bar">
              <span className="difficulty-label">{difficulty}</span>
              <div 
                className="difficulty-progress" 
                style={{ width: `${(count / (stats.totalPapers || 1)) * 100}%` }}
              ></div>
            </div>
          ))}
        </div>
        <div className="type-bars">
          {Object.entries(stats.typeCounts || {}).map(([type, count]) => (
            <div key={type} className="type-bar">
              <span className="type-label">{type}</span>
              <div 
                className="type-progress" 
                style={{ width: `${(count / (stats.totalProjects || 1)) * 100}%` }}
              ></div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Dashboard;