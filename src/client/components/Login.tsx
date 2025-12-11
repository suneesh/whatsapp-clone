import { useState } from 'react';

interface LoginProps {
  onLogin: (username: string, password: string) => void;
  onRegister: (username: string, password: string) => void;
}

function Login({ onLogin, onRegister }: LoginProps) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    
    if (!username.trim() || !password.trim()) {
      setError('Username and password are required');
      return;
    }

    if (username.trim().length < 3) {
      setError('Username must be at least 3 characters');
      return;
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }

    setLoading(true);
    
    try {
      if (isRegistering) {
        await onRegister(username.trim(), password);
      } else {
        await onLogin(username.trim(), password);
      }
    } catch (err: any) {
      setError(err.message || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const toggleMode = () => {
    setIsRegistering(!isRegistering);
    setError('');
  };

  return (
    <div className="login-container">
      <div className="login-box">
        <h1>WhatsApp Clone</h1>
        <h2>{isRegistering ? 'Create Account' : 'Welcome Back'}</h2>
        {error && <div className="error-message">{error}</div>}
        <form onSubmit={handleSubmit}>
          <input
            type="text"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            maxLength={30}
            autoFocus
            disabled={loading}
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={6}
            disabled={loading}
          />
          <button 
            type="submit" 
            disabled={!username.trim() || !password.trim() || loading}
          >
            {loading ? 'Please wait...' : (isRegistering ? 'Sign Up' : 'Sign In')}
          </button>
        </form>
        <div className="toggle-mode">
          <button type="button" onClick={toggleMode} disabled={loading}>
            {isRegistering 
              ? 'Already have an account? Sign In' 
              : "Don't have an account? Sign Up"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default Login;
