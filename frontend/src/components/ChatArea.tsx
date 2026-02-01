import { useState, useRef, useEffect } from 'react';
import { Send, Paperclip, Loader2, Bot, User, Brain, MessageCircle, Pencil } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import { useAuthStore, useChatStore, useUIStore } from '@/lib/store';
import { api, SSE_URL } from '@/lib/api';
import { cn } from '@/lib/utils';

// Simple Message Bubble Component
const MessageBubble = ({ role, content, metadata }: { role: string, content: string, metadata?: any }) => {
  const isUser = role === 'user';
  
  return (
    <div className={cn("flex gap-4 max-w-4xl mx-auto mb-6", isUser ? "flex-row-reverse" : "flex-row")}>
      <div className={cn(
        "w-10 h-10 rounded-full flex items-center justify-center shrink-0 border",
        isUser ? "bg-slate-700 border-slate-600" : "bg-cyan-950/30 border-cyan-500/30 shadow-[0_0_10px_rgba(6,182,212,0.2)]"
      )}>
        {isUser ? <User className="w-5 h-5 text-slate-300" /> : <Bot className="w-5 h-5 text-cyan-400" />}
      </div>
      
      <div className={cn(
        "min-w-0 max-w-[85%] rounded-2xl p-4 shadow-sm",
        isUser ? "bg-slate-700 text-slate-100 rounded-tr-sm" : "bg-slate-800/50 border border-slate-700/50 text-slate-200 rounded-tl-sm backdrop-blur-sm"
      )}>
        {role === 'tool' ? (
          <div className="font-mono text-xs text-cyan-400 bg-black/30 p-2 rounded">
             Running Tool: {metadata?.tool_name || 'Unknown'}
             <pre className="mt-1 text-slate-400 whitespace-pre-wrap">{content}</pre>
          </div>
        ) : (
          <div className="prose prose-invert prose-sm max-w-none prose-p:leading-relaxed prose-pre:bg-slate-900 prose-pre:border prose-pre:border-slate-800">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
          </div>
        )}
        
        {/* Metadata / References Display (Inline for now if needed, but intended for sidebar) */}
        {metadata && metadata.file_name && (
          <div className="mt-2 text-xs text-slate-500 flex items-center gap-1">
            <Paperclip className="w-3 h-3" />
            <span>Ref: {metadata.file_name} (Page {metadata.page})</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default function ChatArea() {
  const { user } = useAuthStore();
  const { messages, addMessage, setMessages, currentConversationId, setCurrentConversationId, setConversations, conversations, updateConversation } = useChatStore();
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [mode, setMode] = useState<"chat" | "agent">("chat");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Edit title state
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const currentConversation = conversations.find(c => c.id === currentConversationId);

  useEffect(() => {
    if (currentConversation) {
        setEditTitle(currentConversation.title);
    }
  }, [currentConversation]);

  const saveTitle = async () => {
    if (!currentConversationId || !editTitle.trim()) {
        setIsEditingTitle(false);
        return;
    }
    
    try {
        updateConversation(currentConversationId, { title: editTitle });
        setIsEditingTitle(false);
        await api.updateConversationTitle(currentConversationId, editTitle);
    } catch (error) {
        console.error("Failed to update title", error);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (currentConversationId) {
      setIsLoading(true);
      api.getMessages(currentConversationId)
        .then(setMessages)
        .catch(console.error)
        .finally(() => setIsLoading(false));
    } else {
      setMessages([]);
    }
  }, [currentConversationId, setMessages]);

  const handleSend = async () => {
    if (!input.trim() || !user || isLoading) return;

    const userMsgContent = input;
    setInput("");
    setIsLoading(true);

    // Optimistic update
    addMessage({
      id: Date.now(),
      role: 'user',
      content: userMsgContent,
      created_at: new Date().toISOString()
    });

    try {
      // 1. Send Message to get ID and create conversation if needed
      const res = await api.sendMessage({
        user_id: user.id,
        conversation_id: currentConversationId || undefined,
        content: userMsgContent,
        mode: currentConversationId ? undefined : mode // Only pass mode for new conv
      });

      if (!currentConversationId) {
        setCurrentConversationId(res.conversation_id);
        // Refresh conversation list so it appears in sidebar
        api.getConversations(user.id).then(setConversations);
      }

      // 2. Start Streaming
      let aiContent = "";
      const aiMsgId = Date.now() + 1;
      
      // Add placeholder AI message
      addMessage({
        id: aiMsgId,
        role: 'assistant',
        content: "",
        created_at: new Date().toISOString()
      });

      await fetchEventSource(SSE_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: user.id,
          conversation_id: res.conversation_id
        }),
        async onopen(response) {
          if (response.ok && response.headers.get('content-type')?.includes('text/event-stream')) {
            return; // everything's good
          } else if (response.status >= 400 && response.status < 500 && response.status !== 429) {
            // client-side errors are usually non-retriable:
            throw new Error("Failed to start stream");
          } else {
            // otherwise we'll retry
            throw new Error("Retriable error");
          }
        },
        onmessage(msg) {
          if (msg.data === "[DONE]") {
            setIsLoading(false);
            return;
          }
          try {
            // Check if msg.data looks like a JSON object
            let data;
            if (msg.data.trim().startsWith('{')) {
                data = JSON.parse(msg.data);
            } else {
                // Backward compatibility or non-JSON chunk
                data = { content: msg.data };
            }
            
            const text = data.content || "";
            aiContent += text;
            
            // Check for references
            if (data.references) {
                 useChatStore.setState(state => {
                    const newMsgs = [...state.messages];
                    const last = newMsgs[newMsgs.length - 1];
                    if (last.role === 'assistant') {
                        last.metadata = { ...last.metadata, references: data.references };
                    }
                    return { messages: newMsgs };
                });
            }

            // Update the last message content
            useChatStore.setState(state => {
              const newMsgs = [...state.messages];
              const last = newMsgs[newMsgs.length - 1];
              if (last.role === 'assistant') {
                last.content = aiContent;
              }
              return { messages: newMsgs };
            });
            
          } catch (e) {
            console.error("Parse error", e);
            // Fallback for plain text just in case
             if (typeof msg.data === 'string') {
                 aiContent += msg.data;
                 useChatStore.setState(state => {
                    const newMsgs = [...state.messages];
                    const last = newMsgs[newMsgs.length - 1];
                    if (last.role === 'assistant') {
                        last.content = aiContent;
                    }
                    return { messages: newMsgs };
                 });
             }
          }
        },
        onclose() {
          setIsLoading(false);
        },
        onerror(err) {
          console.error("Stream error", err);
          setIsLoading(false);
          // Don't retry
          throw err; 
        }
      });

    } catch (error) {
      console.error(error);
      setIsLoading(false);
      alert("Failed to send message");
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !user) return;

    try {
      setIsLoading(true);
      // Determine file type
      if (file.type === 'application/pdf') {
          await api.uploadPdf(user.id, file);
          alert("PDF Uploaded and Ingested Successfully!");
      } else if (file.type.startsWith('image/')) {
          // Upload image to backend
          const res = await api.uploadImage(user.id, file);
          
          // Send a message with the image path to the agent
          // This allows the agent to know about the file and use tools on it
          const imageMsg = `我上传了一张图片，路径是: ${res.file_path}`;
          setInput(imageMsg);
          
          // Optionally add a system message or user message showing the upload
          addMessage({
            id: Date.now(),
            role: 'system',
            content: `图片已上传: ${file.name}`,
            created_at: new Date().toISOString()
          });
      }
    } catch (error) {
      console.error(error);
      alert("Upload failed");
    } finally {
      setIsLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  // Extract references from the last assistant message
  const lastAssistantMessage = messages.slice().reverse().find(m => m.role === 'assistant');
  const currentReferences = lastAssistantMessage?.metadata?.references || [];

  return (
    <div className="flex-1 flex h-screen relative bg-[url('/grid.svg')] bg-repeat opacity-90 overflow-hidden">
        {/* Main Chat Column */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Header */}
          <div className="h-16 border-b border-slate-800 flex items-center px-6 justify-between bg-slate-900/80 backdrop-blur z-10">
            <h2 className="text-lg font-medium text-slate-200 flex items-center gap-2">
              {currentConversationId ? (
                  isEditingTitle ? (
                      <input 
                          autoFocus
                          type="text"
                          value={editTitle}
                          onChange={(e) => setEditTitle(e.target.value)}
                          onBlur={saveTitle}
                          onKeyDown={(e) => e.key === 'Enter' && saveTitle()}
                          className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-sm text-white focus:border-cyan-500 outline-none"
                      />
                  ) : (
                      <div className="flex items-center gap-2 group cursor-pointer" onClick={() => setIsEditingTitle(true)}>
                          <span>{currentConversation?.title || "当前对话"}</span>
                          <Pencil className="w-3 h-3 text-slate-500 opacity-0 group-hover:opacity-100 transition-opacity" />
                      </div>
                  )
              ) : "新对话"}
              {currentConversationId && (
                <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                   ID: {currentConversationId}
                </span>
              )}
            </h2>
            <div className="text-xs text-slate-500 font-mono">RiverAI 智能系统运行中</div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6 scroll-smooth">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-slate-500 opacity-50">
                <Bot className="w-16 h-16 mb-4 text-cyan-500" />
                <p className="text-lg font-medium">RiverAI 系统在线</p>
                <p className="text-sm">准备进行水文分析</p>
              </div>
            )}
            
            {messages.map((m, i) => (
              <MessageBubble key={i} {...m} />
            ))}
            
            {isLoading && messages.length > 0 && messages[messages.length - 1].role === 'user' && (
              <div className="flex gap-4 max-w-4xl mx-auto">
                 <div className="w-10 h-10 rounded-full bg-cyan-950/30 border border-cyan-500/30 flex items-center justify-center">
                    <Loader2 className="w-5 h-5 text-cyan-400 animate-spin" />
                 </div>
                 <div className="flex items-center text-cyan-400 text-sm animate-pulse">
                    正在思考中...
                 </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="p-6 bg-slate-900/80 backdrop-blur border-t border-slate-800">
            <div className="max-w-4xl mx-auto relative group">
              <div className="absolute -inset-0.5 bg-gradient-to-r from-cyan-500 to-blue-600 rounded-xl opacity-20 group-hover:opacity-40 transition duration-500 blur"></div>
              <div className="relative flex items-center bg-slate-900 rounded-xl border border-slate-700 shadow-2xl overflow-hidden">
                
                {/* Mode Selector (Only enabled for new chats or if we want to switch mid-stream - backend supports persistent mode per conv) */}
                {!currentConversationId && (
                  <div className="border-r border-slate-800">
                     <select 
                       value={mode} 
                       onChange={(e) => setMode(e.target.value as any)}
                       className="h-full bg-transparent text-slate-400 text-sm pl-3 pr-8 py-4 focus:ring-0 border-none outline-none cursor-pointer hover:text-cyan-400 transition-colors appearance-none"
                       style={{backgroundImage: 'none'}} // Custom arrow via css or just native
                     >
                       <option value="chat">对话</option>
                       <option value="agent">智能体</option>
                     </select>
                  </div>
                )}

                <button 
                  onClick={() => fileInputRef.current?.click()}
                  className="p-4 text-slate-400 hover:text-cyan-400 transition-colors border-r border-slate-800"
                  title="上传文件"
                >
                  <Paperclip className="w-5 h-5" />
                </button>
                <input 
                  type="file" 
                  ref={fileInputRef} 
                  className="hidden" 
                  accept=".pdf,.jpg,.jpeg,.png" 
                  onChange={handleUpload} 
                />

                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                  placeholder={mode === 'agent' ? "请求智能体分析数据..." : "与 RiverAI 对话..."}
                  className="flex-1 bg-transparent border-none text-slate-200 placeholder-slate-500 focus:ring-0 px-4 py-4 h-full"
                  disabled={isLoading}
                />
                
                <button 
                  onClick={handleSend}
                  disabled={isLoading || !input.trim()}
                  className="p-4 text-cyan-400 hover:text-cyan-300 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                >
                  {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
                </button>
              </div>
            </div>
            <div className="text-center mt-2 text-xs text-slate-600">
               RiverAI v1.0 • Powered by Agno & LanceDB
            </div>
          </div>
        </div>
        
        {/* Right Sidebar for Knowledge */}
        {currentReferences.length > 0 && (
            <div className="w-80 border-l border-slate-800 bg-slate-900/50 backdrop-blur hidden xl:flex flex-col animate-in slide-in-from-right duration-300">
                <div className="h-16 border-b border-slate-800 flex items-center px-4 font-medium text-slate-200">
                    <Brain className="w-4 h-4 mr-2 text-cyan-500"/> 
                    <span>知识库引用</span>
                </div>
                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                    {currentReferences.map((ref: any, idx: number) => (
                        <div key={idx} className="bg-slate-800/50 border border-slate-700 rounded-lg p-3 text-sm hover:border-cyan-500/50 transition-colors">
                            <div className="flex items-center gap-2 mb-2 text-cyan-400 font-medium">
                                <Paperclip className="w-3 h-3" />
                                <span className="truncate" title={ref.meta_data?.file_name || ref.file_name || "未知文档"}>
                                    {ref.meta_data?.file_name || ref.file_name || "未知文档"}
                                </span>
                            </div>
                            <div className="text-slate-400 text-xs line-clamp-4 leading-relaxed bg-black/20 p-2 rounded">
                                {ref.content || "无内容预览"}
                            </div>
                            {ref.page && (
                                <div className="mt-2 text-xs text-slate-500 text-right">
                                    Page {ref.page}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            </div>
        )}
    </div>
  );
}
