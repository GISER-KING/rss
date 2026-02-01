import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, ArrowRight, Eye, EyeOff } from 'lucide-react';
import { api } from '@/lib/api';
import { useAuthStore } from '@/lib/store';
import ParticleRiver from '@/components/ParticleRiver';
import RiverFlow from '@/components/RiverFlow';
import TiltCard from '@/components/TiltCard';
import HolographicOverlay from '@/components/HolographicOverlay';

export default function LoginPage() {
  const navigate = useNavigate();
  const { setAuth } = useAuthStore();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const res = await api.login({ username, password });
      setAuth(res.user, res.access_token);
      navigate('/');
    } catch (err: any) {
      setError(err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0f172a] relative overflow-hidden">
      {/* 1. Holographic HUD Overlay (Top Layer) */}
      <HolographicOverlay />

      {/* 2. Particle River (Middle Layer - Foreground Particles) */}
      <div className="absolute inset-0 z-10">
        <ParticleRiver />
      </div>

      {/* 3. Wave River (Bottom Layer - Background Waves) */}
      <div className="absolute inset-0 z-0 opacity-50">
        <RiverFlow />
      </div>

      {/* 4. Login Card (Interactive Layer) */}
      <TiltCard className="relative z-20 w-full max-w-md">
        <div className="p-8 glass rounded-2xl shadow-2xl border border-slate-700/50 backdrop-blur-xl bg-slate-900/40 relative group">

          {/* Subtle glow behind the card */}
          <div className="absolute -inset-1 bg-gradient-to-r from-cyan-500/20 to-blue-600/20 rounded-2xl blur opacity-20 group-hover:opacity-40 transition duration-500"></div>

          <div className="relative">
            <div className="text-center mb-8">
              <div className="w-16 h-16 bg-gradient-to-tr from-cyan-500 to-blue-600 rounded-2xl mx-auto flex items-center justify-center shadow-[0_0_30px_rgba(6,182,212,0.4)] mb-4 transform rotate-3 group-hover:rotate-6 transition-transform duration-500">
                 <span className="text-3xl font-bold text-white drop-shadow-md">R</span>
              </div>
              <h1 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-white to-slate-400 mb-2 tracking-tight">
                欢迎使用 RiverAI
              </h1>
              <p className="text-slate-400 text-sm">河流岸线空间智能感知系统</p>
            </div>

            <form onSubmit={handleLogin} className="space-y-5">
              {error && (
                <div className="p-3 bg-red-500/10 border border-red-500/20 rounded text-red-400 text-xs text-center">
                  {error === "Login failed" ? "登录失败，请检查用户名或密码" : error}
                </div>
              )}

              <div className="group/input">
                <label className="block text-xs font-medium text-cyan-500/80 mb-1.5 uppercase tracking-wider group-focus-within/input:text-cyan-400 transition-colors">用户名</label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full bg-slate-950/50 border border-slate-700/60 rounded-lg px-4 py-3 text-white focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500/50 outline-none transition-all placeholder:text-slate-600"
                  placeholder="请输入用户名 (admin)"
                  required
                />
              </div>

              <div className="group/input">
                <label className="block text-xs font-medium text-cyan-500/80 mb-1.5 uppercase tracking-wider group-focus-within/input:text-cyan-400 transition-colors">密码</label>
                <div className="relative">
                  <input
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full bg-slate-950/50 border border-slate-700/60 rounded-lg px-4 py-3 text-white focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500/50 outline-none transition-all pr-10 placeholder:text-slate-600"
                    placeholder="请输入密码 (admin123)"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-cyan-400 transition-colors"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3.5 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded-lg font-medium flex items-center justify-center gap-2 transition-all shadow-[0_0_20px_rgba(6,182,212,0.3)] hover:shadow-[0_0_30px_rgba(6,182,212,0.5)] hover:scale-[1.02] active:scale-[0.98] disabled:opacity-70 disabled:cursor-not-allowed mt-4 relative overflow-hidden"
              >
                {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : (
                  <>
                    <span className="relative z-10">登录系统</span>
                    <ArrowRight className="w-4 h-4 relative z-10" />
                    <div className="absolute inset-0 bg-white/20 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700 skew-x-12"></div>
                  </>
                )}
              </button>
            </form>

            <div className="mt-8 text-center text-xs text-slate-600">
              <span className="opacity-50">默认账号: admin / admin123</span>
            </div>
          </div>
        </div>
      </TiltCard>
    </div>
  );
}
