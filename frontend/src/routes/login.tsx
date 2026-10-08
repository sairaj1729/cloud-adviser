import { createFileRoute, Link, useNavigate } from '@tanstack/react-router';
import { useState } from 'react';
import { ArrowRight, Cloud, Eye, EyeOff, LockKeyhole } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { apiLogin } from '@/config/api';

export const Route = createFileRoute('/login')({
  head: () => ({
    meta: [
      { title: 'Sign In | Cloud Advisor' },
      { name: 'description', content: 'Sign in to Cloud Advisor, your multi-cloud cost intelligence workspace.' },
      { property: 'og:title', content: 'Sign In | Cloud Advisor' },
      { property: 'og:description', content: 'Understand cloud spend. Detect waste. Optimize with confidence.' },
      { property: 'og:type', content: 'website' },
      { name: 'twitter:card', content: 'summary_large_image' },
    ],
  }),
  component: Login,
});

function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [visible, setVisible] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ text: string; error?: boolean } | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMessage(null);

    try {
      await apiLogin(email, password);
      setMessage({ text: 'Signed in successfully! Redirecting…' });
      setTimeout(() => navigate({ to: '/' }), 600);
    } catch (err: any) {
      setMessage({ text: err.message || 'Login failed. Check your credentials.', error: true });
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="login-page">
      <div className="login-header">
        <span className="brand-mark">
          <Cloud size={22} />
        </span>
        <strong>
          cloud<span>advisor</span>
        </strong>
      </div>
      <div className="login-layout">
        <div className="login-story">
          <div className="eyebrow">
            <span className="eyebrow-line" /> CLOUD INTELLIGENCE
          </div>
          <h1>
            Clarity across
            <br />
            every cloud.
          </h1>
          <p>
            Understand cloud spend. Detect waste.
            <br />
            Optimize with confidence.
          </p>
          <div className="login-graphic" aria-hidden="true">
            <div className="graphic-line line-one" />
            <div className="graphic-line line-two" />
            <div className="graphic-line line-three" />
            <div className="graphic-node n1" />
            <div className="graphic-node n2" />
            <div className="graphic-node n3" />
            <div className="graphic-node n4" />
          </div>
        </div>
        <div className="login-form-wrap">
          <div className="login-form-head">
            <span className="login-lock">
              <LockKeyhole size={22} />
            </span>
            <h2>Welcome back</h2>
            <p>Enter your details to access your workspace.</p>
          </div>
          <form onSubmit={handleSubmit}>
            <label>
              Email address
              <Input
                type="email"
                autoComplete="username"
                placeholder="you@company.com"
                required
                maxLength={255}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </label>
            <label>
              Password
              <div className="password-wrap">
                <Input
                  type={visible ? 'text' : 'password'}
                  autoComplete="current-password"
                  placeholder="Enter your password"
                  required
                  minLength={4}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
                <Button
                  variant="ghost"
                  size="icon"
                  type="button"
                  aria-label={visible ? 'Hide password' : 'Show password'}
                  onClick={() => setVisible(!visible)}
                >
                  {visible ? <EyeOff size={17} /> : <Eye size={17} />}
                </Button>
              </div>
            </label>
            <div className="login-options">
              <label>
                <input type="checkbox" /> Remember me
              </label>
            </div>
            <Button type="submit" className="login-submit" disabled={loading}>
              {loading ? 'Signing in…' : 'Sign in'} <ArrowRight size={16} />
            </Button>
            {message && (
              <p role="status" className={`login-message ${message.error ? 'text-destructive' : 'text-success'}`}>
                {message.text}
              </p>
            )}
          </form>
          <div className="login-divider">
            <span>OR</span>
          </div>
          <Button asChild variant="outline" className="w-full h-11">
            <Link to="/">Explore workspace <ArrowRight size={15} /></Link>
          </Button>
          <p className="login-footnote">
            New to Cloud Advisor?{' '}
            <Link to="/register" className="text-primary font-medium">
              Create an account
            </Link>
          </p>
        </div>
      </div>
      <footer className="login-footer">
        © 2026 Cloud Advisor <span>Cloud clarity, without the complexity.</span>
      </footer>
    </main>
  );
}
