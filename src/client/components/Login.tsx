import { useState } from 'react';

interface LoginProps {
  onLogin: (username: string) => void;
}

function Login({ onLogin }: LoginProps) {
  const [username, setUsername] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (username.trim()) {
      onLogin(username.trim());
    }
  };

  return (
    <div className="login-container">
      <div className="login-box">
        <h1>WhatsApp Clone</h1>
        <form onSubmit={handleSubmit}>
          <input
            type="text"
            placeholder="Enter your username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            maxLength={30}
            autoFocus
          />
          <button type="submit" disabled={!username.trim()}>
            Continue
          </button>
        </form>
      </div>
    </div>
  );
}

export default Login;
