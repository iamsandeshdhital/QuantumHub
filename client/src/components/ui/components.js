export const Button = ({ children, variant = 'primary', size = 'md', onClick, className, asButton = true }) => {
  const tag = onClick ? 'button' : 'a';
  const variantClasses = {
    primary: 'btn-primary',
    secondary: 'btn-secondary',
    danger: 'btn-danger',
    outline: 'btn-outline',
  };
  const sizeClasses = {
    sm: 'btn-sm',
    md: 'btn-md',
    lg: 'btn-lg',
  };

  return (
    <tag
      className={`btn btn-${variant} ${sizeClasses[size]} ${className || ''}`}
      onClick={onClick}
    >
      {children}
    </tag>
  );
};

Button.displayName = 'Button';

export const Input = ({ type = 'text', placeholder, value, onChange, disabled }) => {
  return (
    <input
      type={type}
      placeholder={placeholder}
      value={value}
      onChange={onChange}
      disabled={disabled}
      className="form-input"
    />
  );
};

Input.displayName = 'Input';

export const Select = ({ options, value, onChange, placeholder }) => {
  return (
    <select value={value} onChange={onChange} className="form-select">
      <option value="" disabled>{placeholder || 'Select...'}</option>
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  );
};

Select.displayName = 'Select';