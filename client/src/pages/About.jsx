import React from 'react';
import { Card } from '../components/ui';

const About = () => {
  return (
    <section className="about-section">
      <div className="about-content">
        <h2>About QuantumHub</h2>
        <p>
          QuantumHub is a comprehensive platform for exploring quantum computing research,
          publications, and implementations. Our mission is to make quantum computing
          knowledge accessible to everyone, from beginners to experts.
        </p>
        <ul className="about-features">
          <li>
            <strong>100+ Papers</strong> from leading institutions and companies
          </li>
          <li>
            <strong>50+ Projects</strong> with implementations and code
          </li>
          <li>
            <strong>Advanced Search</strong> with filtering by type, difficulty, and tags
          </li>
          <li>
            <strong>Real-time Analytics</strong> on research trends
          </li>
        </ul>
        <p className="mission-statement">
          We believe that democratizing quantum computing knowledge will accelerate
          innovation and help build the quantum technologies of tomorrow.
        </p>
      </div>

      <div className="about-stats">
        <div stat-class="stat-item">
          <div stat-class="stat-number">1000+</div>
          <div stat-class="stat-label">Citations</div>
        </div>
        <div stat-class="stat-item">
          <div stat-class="stat-number">50</div>
          <div stat-class="stat-label">Countries</div>
        </div>
        <div stat-class="stat-item">
          <div stat-class="stat-number">2024</div>
          <div stat-class="stat-label">Year Started</div>
        </div>
      </div>

      <footer className="footer">
        <p>
          QuantumHub v1.0.0 · Built with ❤️ for the quantum computing community
        </p>
      </footer>
    </section>
  );
};

export default About;