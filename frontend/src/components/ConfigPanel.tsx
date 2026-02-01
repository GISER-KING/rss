import { useState } from 'react';
import { X, Save, Server, Key } from 'lucide-react';
import { motion } from 'framer-motion';
import { useAuthStore, useUIStore } from '@/lib/store';
import { api } from '@/lib/api';

export default function ConfigPanel() {
  const { user, setAuth } = useAuthStore();
  const { settingsOpen, toggleSettings } = useUIStore();
  
  const [baseUrl, setBaseUrl] = useState(user?.api_base_url || "");
  const [apiKey, setApiKey] = useState(user?.api_key || "");
  const [loading, setLoading] = useState(false);

  if (!settingsOpen) return null;

  const handleSave = async () => {
    if (!user) return;
    setLoading(true);
    try {
      const updatedUser = { ...user, api_base_url: baseUrl, api_key: apiKey };
      await api.updateConfig({ user_id: user.id, api_base_url: baseUrl, api_key: apiKey });
      
      // Update local user state
      if (useAuthStore.getState().token) {
        setAuth(updatedUser, useAuthStore.getState().token!);
      }
      
      alert("Configuration Saved");
      toggleSettings();
    } catch (e) {
      console.error(e);
      alert("Failed to save config");
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div 
      initial={{ x: 300, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 300, opacity: 0 }}
      className="w-80 h-screen glass border-l border-slate-800 flex flex-col absolute right-0 top-0 z-20 shadow-2xl"
    >
      <div className="p-4 border-b border-slate-800 flex items-center justify-between">
        <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider">系统配置</h3>
        <button onClick={toggleSettings} className="text-slate-400 hover:text-white">
          <X className="w-5 h-5" />
        </button>
      </div>

      <div className="p-6 space-y-6 flex-1 overflow-y-auto">
        <div className="space-y-4">
          <h4 className="text-xs font-semibold text-cyan-500 uppercase">大模型服务商</h4>
          
          <div className="space-y-2">
            <label className="text-xs text-slate-400 flex items-center gap-2">
              <Server className="w-3 h-3" /> API 地址 (Base URL)
            </label>
            <input 
              type="text" 
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder="https://api.deepseek.com"
              className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-sm text-white focus:border-cyan-500 outline-none transition-colors"
            />
            <p className="text-[10px] text-slate-500">默认: https://api.deepseek.com</p>
          </div>

          <div className="space-y-2">
            <label className="text-xs text-slate-400 flex items-center gap-2">
              <Key className="w-3 h-3" /> API 密钥 (Key)
            </label>
            <input 
              type="password" 
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-..."
              className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-sm text-white focus:border-cyan-500 outline-none transition-colors"
            />
            <p className="text-[10px] text-slate-500">留空则使用后端默认配置</p>
          </div>
        </div>

        <div className="pt-6 border-t border-slate-800">
           <h4 className="text-xs font-semibold text-cyan-500 uppercase mb-4">知识库引用</h4>
           <p className="text-xs text-slate-500 italic">
             聊天过程中的文档引用将显示在这里。
           </p>
           {/* Placeholder for future RAG context visualization */}
        </div>
      </div>

      <div className="p-4 border-t border-slate-800 bg-slate-900/50">
        <button 
          onClick={handleSave}
          disabled={loading}
          className="w-full py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded font-medium flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
        >
          {loading ? "保存中..." : <><Save className="w-4 h-4" /> 保存配置</>}
        </button>
      </div>
    </motion.div>
  );
}
