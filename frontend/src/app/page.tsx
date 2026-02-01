"use client";

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore, useUIStore } from '@/lib/store';
import Sidebar from '@/components/Sidebar';
import ChatArea from '@/components/ChatArea';
import ConfigPanel from '@/components/ConfigPanel';
import { AnimatePresence } from 'framer-motion';

export default function Home() {
  const router = useRouter();
  const { user, token } = useAuthStore();
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
    if (!token) {
      router.replace('/login');
    }
  }, [token, router]);

  if (!isClient || !token) return null; // or loading spinner

  return (
    <div className="flex h-screen bg-[#0f172a] text-slate-100 overflow-hidden relative">
      <Sidebar />
      <ChatArea />
      <ConfigPanel />
    </div>
  );
}
