import { useAuthStore } from '@/lib/store';
import Sidebar from '@/components/Sidebar';
import ChatArea from '@/components/ChatArea';
import ConfigPanel from '@/components/ConfigPanel';

export default function ChatPage() {
  const { user } = useAuthStore();

  return (
    <div className="flex h-screen bg-[#0f172a] text-slate-100 overflow-hidden relative">
      <Sidebar />
      <ChatArea />
      <ConfigPanel />
    </div>
  );
}
