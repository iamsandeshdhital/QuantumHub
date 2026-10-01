import React from 'react';

export const Card = ({ children, className, style }) => {
  return (
    <div className={`card ${className || ''}`} style={style}>
      {children}
    </div>
  );
};

Card.displayName = 'Card';

export const StatCard = ({ title, count, trend, icon }) => {
  return (
    <div className="stat-card">
      <div className="stat-icon">{icon}</div>
      <div className="stat-count">{count}</div>
      <div className="stat-title">{title}</div>
      {trend && <div className="stat-trend">{trend}</div>}
    </div>
  );
};

StatCard.displayName = 'StatCard';

export const LoadingSpinner = () => {
  return (
    <div className="loading-spinner">
      <div className="spinner-border" role="status">
        <span className="visually-hidden">Loading...</span>
      </div>
    </div>
  );
};

LoadingSpinner.displayName = 'LoadingSpinner';

export const ErrorMessage = ({ error }) => {
  return (
    <div className="error-message">
      <h3>Error</h3>
      <p>{error.message || 'An unexpected error occurred'}</p>
      <button onClick={() => window.history.back()}>Go Back</button>
    </div>
  );
};

ErrorMessage.displayName = 'ErrorMessage';