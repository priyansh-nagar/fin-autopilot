import { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Send, Bot, X } from 'lucide-react';
import { useStore } from '../store/useStore';
import { askFinBot } from '../lib/api';
import type { ParseResult } from '../store/appStore';

export default function AIChat({ isOpen, onClose, parseResult }: { isOpen: boolean; onClose: () => void; parseResult: ParseResult | null }) {
  const { findings } = useStore();
  const [messages, setMessages] = useState<{ role: 'user' | 'assistant'; text: string }[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, loading]);

  const handleSend = async (textOverride?: string) => {
    const userMsg = textOverride || input;
    if (!userMsg.trim()) return;

    const next = [...messages, { role: 'user' as const, text: userMsg }];
    setMessages(next);
    setInput('');
    setLoading(true);

    try {
      const payloadMessages = next.map((m) => ({ role: m.role, content: m.text }));
      const context = {
        findings,
        vendor: parseResult?.data.vendor || [],
        cloud: parseResult?.data.cloud || [],
        procurement: parseResult?.data.procurement || [],
        budget: parseResult?.data.budget || [],
      };
      const result = await askFinBot(payloadMessages, context);
      setMessages((prev) => [...prev, { role: 'assistant', text: result.reply || 'No response returned.' }]);
    } catch (e: any) {
      setMessages((prev) => [...prev, { role: 'assistant', text: `Connection Error: ${e.message}` }]);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <>
      <div className="fixed inset-0 bg-black/60 z-[90] backdrop-blur-sm" onClick={onClose}></div>
      <motion.div initial={{ opacity: 0, x: 100 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 100 }} className="fixed right-0 top-0 bottom-0 w-[450px] bg-[#18181b] z-[100] flex flex-col">
        <div className="p-5 border-b border-zinc-800 flex justify-between items-center bg-zinc-900/50">
          <div className="flex items-center space-x-3"><Bot className="text-violet-400" size={20} /><h3 className="font-semibold text-white">FinBot — Finance AI</h3></div>
          <button onClick={onClose} className="text-zinc-500 hover:text-white"><X size={20} /></button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-5" ref={scrollRef}>
          {messages.length === 0 && <div className="text-zinc-300">Hi CFO! Ask me about detected anomalies and savings opportunities.</div>}
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[85%] p-4 rounded-2xl text-[14px] ${m.role === 'user' ? 'bg-violet-600 text-white' : 'bg-finCard text-zinc-300 border border-zinc-800'}`}>{m.text}</div>
            </div>
          ))}
          {loading && <div className="text-zinc-500">FinBot is thinking...</div>}
        </div>

        <div className="p-4 border-t border-zinc-800 bg-[#18181b]">
          <div className="flex items-center space-x-2">
            <textarea
              className="flex-1 bg-[#27272a] border border-zinc-700 rounded-xl px-4 py-3 text-[15px] text-white resize-none h-[64px]"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="Type your finance query..."
            />
            <button type="button" onClick={() => handleSend()} disabled={!input.trim() || loading} className="h-[64px] w-[64px] bg-violet-600 disabled:opacity-50 rounded-xl text-white flex items-center justify-center">
              <Send size={20} />
            </button>
          </div>
        </div>
      </motion.div>
    </>
  );
}
