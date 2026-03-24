import { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Send, Bot, X } from 'lucide-react';
import { useStore } from '../store/useStore';

export default function AIChat({ isOpen, onClose }: { isOpen: boolean, onClose: () => void }) {
  const store = useStore();
  const [messages, setMessages] = useState<{role: 'user'|'model', text: string}[]>([]);
  const [geminiHistory, setGeminiHistory] = useState<{role: 'user'|'model', parts: [{text: string}]}[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [isSwitchedOff, setIsSwitchedOff] = useState(false);
  const [chips, setChips] = useState<string[]>([
    "Which dept is over budget?", 
    "Top 3 savings actions", 
    "Summarise vendor anomalies", 
    "Explain the cloud spike"
  ]);
  const scrollRef = useRef<HTMLDivElement>(null);

  const SYSTEM_PROMPT = `You are "FinBot — financial AI for Fin-Autopilot".
You are a finance-only AI. You ONLY answer questions about: enterprise cost management, procurement, vendor payments, cloud spend, budgets, GST/TDS compliance, accounts payable/receivable, P&L, cash flow, financial reporting, and guiding the user through this website.

For ANY off-topic question (coding, travel, food, general knowledge, personal advice etc.), respond ONLY with:
'I am FinBot, specialised in enterprise finance and this platform. That is outside my scope. Based on your data, I can help you with: [suggest 2 specific things visible in their uploaded data or guide you through the site].'

Always use Indian financial terminology: lakh, crore, FY, GST, TDS.
Always lead with the INR figure. End every response with one 'Recommended next action:' line.
Reference actual INR figures and vendor names from the data provided below.`;

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, loading]);

  const handleSend = async (textOveride?: string) => {
    const userMsg = textOveride || input;
    if (!userMsg.trim()) return;
    
    setMessages(prev => [...prev, { role: 'user', text: userMsg }]);
    setInput('');
    setLoading(true);
    setChips([]);

    try {
      // Fallback API key to my default or free tier API key format as requested
      const apiKey = (import.meta as any).env.VITE_GEMINI_API_KEY || "AIzaSy_AntigravityPlaceholderKey_PleaseReplace";
      if (!apiKey) throw new Error("VITE_GEMINI_API_KEY is not defined.");

      const payload = {
        contents: [
          { 
            role: "user", 
            parts: [{ text: SYSTEM_PROMPT + "\n\nDATA:\n" + JSON.stringify({
              findings: store.findings,
              vendorRows: store.vendorRows.slice(0, 100), // Cap size
              cloudRows: store.cloudRows.slice(0, 100),
              procRows: store.procRows.slice(0, 100),
              budgetRows: store.budgetRows.slice(0, 100)
            }) }] 
          },
          ...geminiHistory,
          { role: "user", parts: [{ text: userMsg }] }
        ],
        // Use as less credits as possible
        generationConfig: { maxOutputTokens: 200, temperature: 0.2 }
      };

      const res = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${apiKey}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        if (res.status === 429 || res.status === 400 || res.status === 403) {
          setIsSwitchedOff(true);
          setMessages(prev => [...prev, { role: 'model', text: "AI has been switched off because credits have run out or the API key is unavailable." }]);
          setChips([]);
          return;
        }
        const errDump = await res.text();
        console.error("Gemini API Error:", errDump);
        throw new Error(`API Error ${res.status}`);
      }
      
      const data = await res.json();
      const botReply = data.candidates?.[0]?.content?.parts?.[0]?.text || "Sorry, I couldn't generate a response.";

      setMessages(prev => [...prev, { role: 'model', text: botReply }]);
      setGeminiHistory(prev => [
        ...prev, 
        { role: 'user', parts: [{ text: userMsg }]},
        { role: 'model', parts: [{ text: botReply }]}
      ]);

      // Generate 2 follow up chips dynamically based on context locally
      const contextKeywords = botReply.toLowerCase();
      const nextChips = [];
      if (contextKeywords.includes("vendor") || contextKeywords.includes("procurement")) {
        nextChips.push("Show me the PO variances");
        nextChips.push("How to consolidate duplicates?");
      } else if (contextKeywords.includes("cloud") || contextKeywords.includes("ec2")) {
        nextChips.push("What's driving the compute spike?");
        nextChips.push("List all idle buckets");
      } else if (contextKeywords.includes("budget")) {
        nextChips.push("Which dept is bleeding most?");
        nextChips.push("How to mitigate actuals variance?");
      } else {
        nextChips.push("What's the total waste?");
        nextChips.push("Explain the biggest single anomaly");
      }
      setChips(nextChips);

    } catch (e: any) {
      console.error(e);
      setMessages(prev => [...prev, { role: 'model', text: `Connection Error: ${e.message}. (Ensure VITE_GEMINI_API_KEY is active).` }]);
      setChips(["Retry connection", "Summarise vendor anomalies"]);
    } finally {
      setLoading(false);
    }
  };

  const parseMarkdown = (text: string) => {
    return text.split('\n').map((str, i) => {
      const parts = str.split(/(\*\*.*?\*\*)/).map((part, j) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return <strong key={j} className="text-white font-semibold">{part.slice(2, -2)}</strong>;
        }
        return part;
      });
      return <p key={i} className="mb-2 last:mb-0 leading-relaxed text-zinc-300">{parts}</p>;
    });
  };

  if (!isOpen) return null;

  return (
    <>
      <div className="fixed inset-0 bg-black/60 z-[90] backdrop-blur-sm" onClick={onClose}></div>
      <motion.div 
        initial={{ opacity: 0, x: 100 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: 100 }}
        className="fixed right-0 top-0 bottom-0 w-[450px] bg-[#18181b] shadow-[0_0_50px_rgba(0,0,0,0.8)] z-[100] flex flex-col"
      >
      <div className="p-5 border-b border-zinc-800 flex justify-between items-center bg-zinc-900/50">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-violet-500/20 rounded-lg">
            <Bot className="text-violet-400" size={20} />
          </div>
          <div>
             <h3 className="font-semibold text-white">FinBot — Finance AI</h3>
             <span className="text-[10px] uppercase tracking-wider text-emerald-500 flex items-center mt-0.5"><div className="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1 animate-pulse" /> Online Context Engine</span>
          </div>
        </div>
        <button onClick={onClose} className="text-zinc-500 hover:text-white transition-colors bg-zinc-800/50 hover:bg-zinc-700/50 p-2 rounded-lg">
          <X size={20} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-5 space-y-5" ref={scrollRef}>
        {messages.length === 0 && (
          <div className="flex justify-start">
             <div className="w-8 h-8 rounded-full bg-violet-600 flex items-center justify-center mr-3 mt-1 flex-shrink-0"><Bot size={16} className="text-white" /></div>
             <div className="max-w-[85%] p-4 rounded-2xl text-[14px] bg-finCard text-zinc-300 border border-zinc-800 rounded-bl-none shadow-sm">
               Hi CFO! I am FinBot, your dedicated Fin-Autopilot AI. I have ingested your parsed data stores. How can I help optimize your P&L today?
             </div>
          </div>
        )}
        
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
             {m.role === 'model' && <div className="w-8 h-8 rounded-full bg-violet-600 flex items-center justify-center mr-3 mt-1 flex-shrink-0 shadow-lg shadow-violet-900/20"><Bot size={16} className="text-white" /></div>}
             <div className={`max-w-[85%] p-4 rounded-2xl text-[14px] ${
              m.role === 'user' ? 'bg-violet-600 text-white rounded-br-none shadow-md shadow-violet-900/10 font-medium' : 'bg-finCard text-zinc-300 border border-zinc-800 rounded-bl-none shadow-sm'
            }`}>
              {parseMarkdown(m.text)}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
             <div className="w-8 h-8 rounded-full bg-violet-600 flex items-center justify-center mr-3 mt-1 shadow-lg shadow-violet-900/20"><Bot size={16} className="text-white" /></div>
             <div className="bg-finCard border border-zinc-800 p-4 rounded-2xl rounded-bl-none items-center flex">
               <motion.div animate={{ opacity: [0.3, 1, 0.3] }} transition={{ repeat: Infinity, duration: 1.5 }} className="flex space-x-1.5">
                 <div className="w-2 h-2 bg-violet-400 rounded-full"></div>
                 <div className="w-2 h-2 bg-violet-400 rounded-full"></div>
                 <div className="w-2 h-2 bg-violet-400 rounded-full"></div>
               </motion.div>
             </div>
          </div>
        )}

        {/* Suggested Chips */}
        {chips.length > 0 && !loading && (
          <div className="flex flex-wrap gap-2 justify-end mt-4">
            {chips.map((chip, idx) => (
              <button 
                key={idx} 
                onClick={() => handleSend(chip)}
                className="text-xs bg-violet-900/30 hover:bg-violet-600/50 text-violet-300 border border-violet-800/50 px-3 py-1.5 rounded-full transition-all"
              >
                {chip}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="p-4 border-t border-zinc-800 bg-[#18181b]">
        <div className="text-[11px] text-zinc-500 mb-2 uppercase tracking-wide font-semibold pl-1">Answers finance questions only</div>
        <div className="flex items-center space-x-2">
          <textarea 
            autoFocus
            disabled={isSwitchedOff}
            className="flex-1 bg-[#27272a] border border-zinc-700 rounded-xl px-4 py-3 text-[15px] focus:outline-none focus:border-violet-500 text-white placeholder:text-zinc-500 resize-none h-[64px] disabled:opacity-50 disabled:cursor-not-allowed"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder={isSwitchedOff ? "AI is currently switched off." : "Type your query..."}
            style={{ color: '#ffffff' }}
          />
          <button type="button" onClick={() => handleSend()} disabled={!input.trim() || loading || isSwitchedOff} className="h-[64px] w-[64px] bg-violet-600 hover:bg-violet-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-xl transition-all shadow-lg text-white font-medium flex items-center justify-center shrink-0">
             <Send size={20} className={input.trim() && !loading && !isSwitchedOff ? "translate-x-0.5" : ""} />
          </button>
        </div>
      </div>
    </motion.div>
    </>
  );
}
