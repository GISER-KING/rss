import { useEffect } from 'react';
import { MessageSquare, Plus, Settings, LogOut, User as UserIcon, Trash2, Bot, MessageCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuthStore, useChatStore, useUIStore } from '@/lib/store';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

export default function Sidebar() {
  const { user, logout } = useAuthStore();
  const { conversations, setConversations, currentConversationId, setCurrentConversationId, deleteConversation } = useChatStore();
  const { sidebarOpen, toggleSettings } = useUIStore();

  useEffect(() => {
    if (user) {
      api.getConversations(user.id).then(setConversations).catch(console.error);
    }
  }, [user, setConversations]);

  const handleNewChat = () => {
    setCurrentConversationId(null);
  };

  const handleDelete = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this conversation?")) return;
    try {
      await api.deleteConversation(id);
      deleteConversation(id);
    } catch (error) {
      console.error("Failed to delete conversation", error);
    }
  };

  if (!sidebarOpen) return null;

  return (
    <motion.div 
      initial={{ x: -300, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: -300, opacity: 0 }}
      className="w-64 h-screen glass flex flex-col border-r border-slate-800"
    >
      {/* Logo */}
      <div className="p-4 border-b border-slate-800 flex items-center gap-2">
        <div className="w-8 h-8 rounded-full bg-cyan-500 shadow-[0_0_15px_rgba(6,182,212,0.5)] flex items-center justify-center">
          <span className="text-white font-bold text-lg">R</span>
        </div>
        <h1 className="text-xl font-bold text-slate-100 tracking-wider">RiverAI</h1>
      </div>

      {/* New Chat Button */}
      <div className="p-4">
        <button 
          onClick={handleNewChat}
          className="w-full py-3 px-4 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-cyan-500/50 transition-all flex items-center gap-2 group"
        >
          <Plus className="w-5 h-5 text-cyan-400 group-hover:text-cyan-300" />
          <span className="text-sm font-medium text-slate-300 group-hover:text-white">新建对话</span>
        </button>
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto px-2 space-y-1">
        {conversations.map((c) => (
          <div
            key={c.id}
            onClick={() => setCurrentConversationId(c.id)}
            className={cn(
              "w-full text-left py-3 px-3 rounded-md text-sm transition-colors flex items-center gap-3 truncate cursor-pointer group relative",
              currentConversationId === c.id 
                ? "bg-cyan-900/20 text-cyan-400 border border-cyan-500/20" 
                : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
            )}
          >
            {c.mode === 'agent' ? <Bot className="w-4 h-4 shrink-0" /> : <MessageCircle className="w-4 h-4 shrink-0" />}
            <span className="truncate flex-1">{c.title}</span>
            
            <button
              onClick={(e) => handleDelete(e, c.id)}
              className="opacity-0 group-hover:opacity-100 p-1 hover:text-red-400 hover:bg-slate-900 rounded transition-all"
              title="删除"
            >
              <Trash2 className="w-3 h-3" />
            </button>
          </div>
        ))}
      </div>

      {/* User Profile */}
      <div className="p-4 border-t border-slate-800 bg-slate-900/50">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-full bg-slate-700 flex items-center justify-center border border-slate-600">
            <UserIcon className="w-5 h-5 text-slate-300" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate">{user?.username}</p>
            <p className="text-xs text-slate-500 truncate">{user?.role}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <button 
            onClick={toggleSettings}
            className="flex-1 py-2 rounded bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 flex items-center justify-center gap-1 transition-colors"
          >
            <Settings className="w-3 h-3" /> 配置
          </button>
          <button 
            onClick={logout}
            className="flex-1 py-2 rounded bg-slate-800 hover:bg-red-900/20 text-xs text-slate-300 hover:text-red-400 flex items-center justify-center gap-1 transition-colors"
          >
            <LogOut className="w-3 h-3" /> 退出
          </button>
        </div>
      </div>
    </motion.div>
  );
}
