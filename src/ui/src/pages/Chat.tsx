import { useState, useRef, useEffect } from 'react';
import { chatWithAgent } from '@/lib/api';
import { Send, Bot, User, Loader2 } from 'lucide-react';
import clsx from 'clsx';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { CodeBlock } from '@/components/CodeBlock';

interface Message {
    role: 'user' | 'assistant';
    content: string;
}

export default function Chat() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [sessionId, setSessionId] = useState<string>('');
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLInputElement>(null);

    // Use 'convo' agent by default
    const agentId = 'convo';

    // Initialize session ID on mount
    useEffect(() => {
        setSessionId(crypto.randomUUID());
    }, []);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // Focus input on load
    useEffect(() => {
        setTimeout(() => inputRef.current?.focus(), 100);
    }, []);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || loading) return;

        const userMsg = input;
        setInput('');
        setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
        setLoading(true);

        try {
            const result = await chatWithAgent(sessionId, agentId, userMsg);
            setMessages(prev => [...prev, { role: 'assistant', content: result.content }]);
        } catch (err) {
            console.error(err);
            setMessages(prev => [...prev, { role: 'assistant', content: 'Error: Failed to get response. Is the backend running?' }]);
        } finally {
            setLoading(false);
            // Keep focus for continuous chatting
            setTimeout(() => inputRef.current?.focus(), 100);
        }
    };

    return (
        <div className="flex flex-col h-[calc(100vh-4rem)]">
            <div className="mb-4">
                <h1 className="text-3xl font-bold mb-2">Chat</h1>
                <p className="text-gray-500">Start a conversation with your AI assistant.</p>
            </div>

            <div className="flex-1 bg-white rounded-2xl border border-gray-100 shadow-sm p-6 overflow-hidden flex flex-col">
                <div className="flex-1 overflow-y-auto space-y-6 pr-2">
                    {messages.length === 0 && (
                        <div className="h-full flex flex-col items-center justify-center text-gray-400 opacity-50">
                            <Bot size={64} className="mb-4" />
                            <p>Start a conversation</p>
                        </div>
                    )}

                    {messages.map((msg, idx) => (
                        <div key={idx} className={clsx("flex gap-4", msg.role === 'user' ? "flex-row-reverse" : "")}>
                            <div className={clsx(
                                "w-8 h-8 rounded-full flex items-center justify-center shrink-0",
                                msg.role === 'user' ? "bg-gray-200" : "bg-brand-blue text-white"
                            )}>
                                {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
                            </div>

                            <div className={clsx(
                                "py-3 px-4 rounded-2xl max-w-[80%] overflow-hidden",
                                msg.role === 'user'
                                    ? "bg-gray-100 text-gray-900 rounded-tr-sm"
                                    : "bg-blue-50 text-slate-800 rounded-tl-sm"
                            )}>
                                <div className="prose prose-sm max-w-none prose-p:leading-relaxed">
                                    <ReactMarkdown
                                        remarkPlugins={[remarkGfm]}
                                        components={{
                                            code: CodeBlock,
                                            pre: ({ children }: any) => <>{children}</>,
                                        }}
                                    >
                                        {msg.content}
                                    </ReactMarkdown>
                                </div>
                            </div>
                        </div>
                    ))}
                    {loading && (
                        <div className="flex gap-4">
                            <div className="w-8 h-8 rounded-full bg-brand-blue text-white flex items-center justify-center shrink-0">
                                <Bot size={16} />
                            </div>
                            <div className="bg-gray-50 py-3 px-4 rounded-2xl rounded-tl-sm flex items-center">
                                <Loader2 className="animate-spin text-gray-400" size={16} />
                            </div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                <div className="mt-4 pt-4 border-t border-gray-100">
                    <form onSubmit={handleSubmit} className="flex gap-2">
                        <input
                            ref={inputRef}
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            placeholder="Type your message..."
                            className="flex-1 bg-gray-50 border border-transparent focus:bg-white focus:border-brand-blue outline-none rounded-xl px-4 py-3 transition-all"
                            disabled={loading}
                        />
                        <button
                            type="submit"
                            disabled={loading || !input.trim()}
                            className="bg-brand-blue text-white p-3 rounded-xl hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            <Send size={20} />
                        </button>
                    </form>
                </div>
            </div>
        </div>
    );
}
