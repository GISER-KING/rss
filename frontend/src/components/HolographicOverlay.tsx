"use client";

import { motion } from "framer-motion";
import { useEffect, useState } from "react";

export default function HolographicOverlay() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  return (
    <div className="absolute inset-0 pointer-events-none z-10 overflow-hidden">
      {/* 1. CRT/Grid Pattern Overlay */}
      <div 
        className="absolute inset-0 opacity-[0.03]" 
        style={{
            backgroundImage: "linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06))",
            backgroundSize: "100% 2px, 3px 100%"
        }}
      />

      {/* 2. Corner Tech Decorations */}
      {/* Top Left */}
      <div className="absolute top-8 left-8 flex flex-col gap-1">
         <div className="flex items-center gap-2">
            <motion.div 
                className="w-2 h-2 bg-cyan-500 rounded-full"
                animate={{ opacity: [1, 0.2, 1] }}
                transition={{ duration: 2, repeat: Infinity }}
            />
            <span className="text-[10px] font-mono text-cyan-500/60 tracking-widest">SYSTEM ONLINE</span>
         </div>
         <div className="w-32 h-[1px] bg-cyan-500/20" />
      </div>

      {/* Top Right */}
      <div className="absolute top-8 right-8 text-right">
         <span className="text-[10px] font-mono text-cyan-500/60 tracking-widest block mb-1">SECURE_LINK</span>
         <div className="flex justify-end gap-1">
            {[...Array(5)].map((_, i) => (
                <motion.div 
                    key={i}
                    className="w-1 h-3 bg-cyan-500/40"
                    animate={{ height: [4, 12, 4], opacity: [0.3, 0.8, 0.3] }}
                    transition={{ duration: 1.5, repeat: Infinity, delay: i * 0.1 }}
                />
            ))}
         </div>
      </div>

      {/* Bottom Left */}
      <div className="absolute bottom-8 left-8">
         <div className="flex gap-2 text-[9px] font-mono text-cyan-500/40">
            <span>CPU: 34%</span>
            <span>MEM: 512TB</span>
            <span>NET: 10Gbps</span>
         </div>
         <div className="mt-1 w-48 h-[2px] bg-gradient-to-r from-cyan-500/40 to-transparent" />
      </div>

      {/* Bottom Right */}
      <div className="absolute bottom-8 right-8">
         <motion.div 
            className="w-16 h-16 border border-cyan-500/20 rounded-full border-t-cyan-500 border-r-transparent animate-spin"
            animate={{ rotate: 360 }}
            transition={{ duration: 10, repeat: Infinity, ease: "linear" }}
         />
      </div>
      
      {/* 4. Vignette */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_40%,rgba(15,23,42,0.8)_100%)]"></div>
    </div>
  );
}
