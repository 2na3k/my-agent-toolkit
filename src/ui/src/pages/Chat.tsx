import { useState, useRef, useEffect } from 'react';
import {
    createConversation,
    listConversations,
    getConversationMessages,
    sendChatMessage,
    deleteConversation,
    updateConversation,
    type Conversation,
    type Message,
} from '@/lib/api';
import {
    Send,
    Bot,
    User,
    Loader2,
    Plus,
    Trash2,
    Edit2,
    Check,
    X,
    MessageSquare,
    GripVertical,
} from 'lucide-react';
import clsx from 'clsx';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { CodeBlock } from '@/components/CodeBlock';

export default function Chat() {
    const [conversations, setConversations] = useState<Conversation[]>([]);
    const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [loadingConversations, setLoadingConversations] = useState(true);
    const [loadingMessages, setLoadingMessages] = useState(false);
    const [editingConversationId, setEditingConversationId] = useState<string | null>(null);
    const [editingTitle, setEditingTitle] = useState('');
    const [sidebarWidth, setSidebarWidth] = useState(320);
    const [isResizing, setIsResizing] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLInputElement>(null);
    const sidebarRef = useRef<HTMLDivElement>(null);
    const startXRef = useRef<number>(0);
    const startWidthRef = useRef<number>(320);

    // Use 'convo' agent by default
    const agentId = 'convo';

    // Resize handler
    const handleResizeStart = (e: React.MouseEvent) => {
        e.preventDefault();
        setIsResizing(true);
        startXRef.current = e.clientX;
        startWidthRef.current = sidebarWidth;
    };

    useEffect(() => {
        const handleMouseMove = (e: MouseEvent) => {
            if (!isResizing) return;

            const deltaX = e.clientX - startXRef.current;
            const newWidth = startWidthRef.current + deltaX;

            // Min width: 250px, Max width: 600px
            if (newWidth >= 250 && newWidth <= 600) {
                setSidebarWidth(newWidth);
            }
        };

        const handleMouseUp = () => {
            setIsResizing(false);
        };

        if (isResizing) {
            document.addEventListener('mousemove', handleMouseMove);
            document.addEventListener('mouseup', handleMouseUp);
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
        }

        return () => {
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        };
    }, [isResizing, sidebarWidth]);

    // Load conversations on mount
    useEffect(() => {
        loadConversations();
    }, []);

    // Load messages when conversation changes
    useEffect(() => {
        if (currentConversationId) {
            loadMessages(currentConversationId);
        } else {
            setMessages([]);
        }
    }, [currentConversationId]);

    const loadConversations = async () => {
        try {
            setLoadingConversations(true);
            const data = await listConversations(agentId, 50);
            setConversations(data);

            // If no current conversation and we have conversations, select the first one
            if (!currentConversationId && data.length > 0) {
                setCurrentConversationId(data[0].id);
            }
        } catch (err) {
            console.error('Failed to load conversations:', err);
        } finally {
            setLoadingConversations(false);
        }
    };

    const loadMessages = async (conversationId: string) => {
        try {
            setLoadingMessages(true);
            const data = await getConversationMessages(conversationId);
            setMessages(data);
        } catch (err) {
            console.error('Failed to load messages:', err);
            setMessages([]);
        } finally {
            setLoadingMessages(false);
        }
    };

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // Focus input when conversation changes
    useEffect(() => {
        setTimeout(() => inputRef.current?.focus(), 100);
    }, [currentConversationId]);

    const handleCreateNewConversation = async () => {
        try {
            const newConversation = await createConversation(agentId);
            setConversations([newConversation, ...conversations]);
            setCurrentConversationId(newConversation.id);
        } catch (err) {
            console.error('Failed to create conversation:', err);
        }
    };

    const handleDeleteConversation = async (conversationId: string, e: React.MouseEvent) => {
        console.log('Delete requested for:', conversationId);
        e.stopPropagation();
        e.preventDefault();

        if (!confirm('Are you sure you want to delete this conversation?')) {
            console.log('Delete cancelled');
            return;
        }

        try {
            console.log('Calling API to delete:', conversationId);
            await deleteConversation(conversationId);

            // Single functional update to state
            setConversations(prev => {
                const updated = prev.filter(c => c.id !== conversationId);

                // If we deleted the current conversation, select another one
                if (currentConversationId === conversationId) {
                    if (updated.length > 0) {
                        setCurrentConversationId(updated[0].id);
                    } else {
                        setCurrentConversationId(null);
                    }
                }
                return updated;
            });

            console.log('Delete successful');
        } catch (err) {
            console.error('Failed to delete conversation:', err);
            alert('Failed to delete conversation. Please check if the backend is running.');
        }
    };

    const handleStartEditTitle = (conversation: Conversation, e: React.MouseEvent) => {
        e.stopPropagation();
        setEditingConversationId(conversation.id);
        setEditingTitle(conversation.title || '');
    };

    const handleSaveTitle = async (conversationId: string) => {
        if (!editingTitle.trim()) {
            setEditingConversationId(null);
            return;
        }

        try {
            await updateConversation(conversationId, editingTitle.trim());
            setConversations(
                conversations.map((c) =>
                    c.id === conversationId ? { ...c, title: editingTitle.trim() } : c
                )
            );
            setEditingConversationId(null);
        } catch (err) {
            console.error('Failed to update conversation title:', err);
        }
    };

    const handleCancelEdit = () => {
        setEditingConversationId(null);
        setEditingTitle('');
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || loading || !currentConversationId) return;

        const userMsg = input;
        setInput('');

        // Optimistically add user message
        const optimisticUserMessage: Message = {
            id: Date.now(),
            conversation_id: currentConversationId,
            role: 'user',
            content: userMsg,
            timestamp: new Date().toISOString(),
            metadata: {},
            token_count: null,
        };
        setMessages((prev) => [...prev, optimisticUserMessage]);
        setLoading(true);

        try {
            const result = await sendChatMessage(currentConversationId, userMsg);

            // Add assistant message
            const assistantMessage: Message = {
                id: Date.now() + 1,
                conversation_id: currentConversationId,
                role: 'assistant',
                content: result.assistant_message,
                timestamp: new Date().toISOString(),
                metadata: {},
                token_count: null,
            };
            setMessages((prev) => [...prev, assistantMessage]);

            // Update conversation list to reflect new message count
            await loadConversations();
        } catch (err) {
            console.error(err);
            const errorMessage: Message = {
                id: Date.now() + 1,
                conversation_id: currentConversationId,
                role: 'assistant',
                content: 'Error: Failed to get response. Is the backend running?',
                timestamp: new Date().toISOString(),
                metadata: {},
                token_count: null,
            };
            setMessages((prev) => [...prev, errorMessage]);
        } finally {
            setLoading(false);
            setTimeout(() => inputRef.current?.focus(), 100);
        }
    };

    const getConversationTitle = (conversation: Conversation) => {
        if (conversation.title) {
            return conversation.title;
        }
        const date = new Date(conversation.created_at);
        return `Chat ${date.toLocaleDateString()} ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    };

    return (
        <div className="flex h-[calc(100vh-4rem)] gap-0 relative">
            {/* Conversation History Sidebar */}
            <div
                ref={sidebarRef}
                style={{
                    width: `${sidebarWidth}px`,
                }}
                className="bg-white rounded-l-2xl border border-gray-100 shadow-sm flex flex-col overflow-hidden transition-none"
            >
                <div className="flex-1 overflow-y-auto p-2">
                    {loadingConversations ? (
                        <div className="flex items-center justify-center h-32">
                            <Loader2 className="animate-spin text-gray-400" size={24} />
                        </div>
                    ) : conversations.length === 0 ? (
                        <div className="flex flex-col items-center justify-center h-32 text-gray-400 text-sm px-4">
                            <MessageSquare size={32} className="mb-2 opacity-50" />
                            <p className="text-center">No conversations yet</p>
                            <p className="text-xs mt-1 text-center">Click below to create one</p>
                        </div>
                    ) : (
                        <div className="space-y-1">
                            {conversations.map((conversation) => (
                                <div
                                    key={conversation.id}
                                    onClick={() => setCurrentConversationId(conversation.id)}
                                    className={clsx(
                                        'group p-3 rounded-lg cursor-pointer transition-all',
                                        currentConversationId === conversation.id
                                            ? 'bg-blue-50 border border-brand-blue'
                                            : 'hover:bg-gray-50 border border-transparent'
                                    )}
                                >
                                    {editingConversationId === conversation.id ? (
                                        <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                                            <input
                                                type="text"
                                                value={editingTitle}
                                                onChange={(e) => setEditingTitle(e.target.value)}
                                                onKeyDown={(e) => {
                                                    if (e.key === 'Enter') {
                                                        handleSaveTitle(conversation.id);
                                                    } else if (e.key === 'Escape') {
                                                        handleCancelEdit();
                                                    }
                                                }}
                                                className="flex-1 px-2 py-1 text-sm border border-brand-blue rounded outline-none"
                                                autoFocus
                                            />
                                            <button
                                                onClick={() => handleSaveTitle(conversation.id)}
                                                className="p-1 hover:bg-green-100 rounded text-green-600"
                                            >
                                                <Check size={16} />
                                            </button>
                                            <button
                                                onClick={handleCancelEdit}
                                                className="p-1 hover:bg-red-100 rounded text-red-600"
                                            >
                                                <X size={16} />
                                            </button>
                                        </div>
                                    ) : (
                                        <>
                                            <div className="flex items-start justify-between gap-2 mb-1">
                                                <h3 className="font-medium text-sm line-clamp-1 flex-1">
                                                    {getConversationTitle(conversation)}
                                                </h3>
                                                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                                    <button
                                                        type="button"
                                                        onClick={(e) => handleStartEditTitle(conversation, e)}
                                                        className="p-1.5 hover:bg-blue-100 rounded text-gray-600 hover:text-brand-blue"
                                                        title="Rename"
                                                    >
                                                        <Edit2 size={14} />
                                                    </button>
                                                    <button
                                                        type="button"
                                                        onClick={(e) => handleDeleteConversation(conversation.id, e)}
                                                        className="p-1.5 hover:bg-red-100 rounded text-gray-600 hover:text-red-600"
                                                        title="Delete"
                                                    >
                                                        <Trash2 size={14} />
                                                    </button>
                                                </div>
                                            </div>
                                            <div className="flex items-center justify-between text-xs text-gray-500">
                                                <span>{conversation.message_count} messages</span>
                                                <span>{new Date(conversation.updated_at).toLocaleDateString()}</span>
                                            </div>
                                        </>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* New Conversation Button at Bottom */}
                <div className="p-4 border-t border-gray-100 bg-gray-50/50">
                    <button
                        type="button"
                        onClick={handleCreateNewConversation}
                        className="w-full bg-brand-blue text-white px-4 py-2.5 rounded-xl hover:bg-blue-600 transition-colors flex items-center justify-center gap-2 font-medium"
                    >
                        <Plus size={20} />
                        New Conversation
                    </button>
                </div>
            </div>

            {/* Resize Handle */}
            <div
                onMouseDown={handleResizeStart}
                className={clsx(
                    'w-1 bg-gray-200 hover:bg-brand-blue cursor-col-resize flex items-center justify-center group transition-colors relative',
                    isResizing && 'bg-brand-blue'
                )}
            >
                <div className="absolute inset-y-0 -left-1 -right-1 flex items-center justify-center">
                    <GripVertical
                        size={16}
                        className={clsx(
                            'text-gray-400 group-hover:text-brand-blue transition-colors',
                            isResizing && 'text-brand-blue'
                        )}
                    />
                </div>
            </div>

            {/* Chat Area */}
            <div className="flex-1 flex flex-col pl-4">
                <div className="mb-4">
                    <h1 className="text-3xl font-bold mb-2">Chat</h1>
                    <p className="text-gray-500">
                        {currentConversationId
                            ? 'Continue your conversation with the AI assistant.'
                            : 'Create a new conversation to get started.'}
                    </p>
                </div>

                <div className="flex-1 bg-white rounded-2xl border border-gray-100 shadow-sm p-6 overflow-hidden flex flex-col">
                    <div className="flex-1 overflow-y-auto space-y-6 pr-2">
                        {!currentConversationId ? (
                            <div className="h-full flex flex-col items-center justify-center text-gray-400 opacity-50">
                                <MessageSquare size={64} className="mb-4" />
                                <p className="text-lg font-medium mb-2">No conversation selected</p>
                                <p className="text-sm">Create a new conversation or select an existing one</p>
                            </div>
                        ) : loadingMessages ? (
                            <div className="h-full flex items-center justify-center">
                                <Loader2 className="animate-spin text-gray-400" size={32} />
                            </div>
                        ) : messages.length === 0 ? (
                            <div className="h-full flex flex-col items-center justify-center text-gray-400 opacity-50">
                                <Bot size={64} className="mb-4" />
                                <p>Start a conversation</p>
                            </div>
                        ) : (
                            messages.map((msg) => (
                                <div
                                    key={msg.id}
                                    className={clsx('flex gap-4', msg.role === 'user' ? 'flex-row-reverse' : '')}
                                >
                                    <div
                                        className={clsx(
                                            'w-8 h-8 rounded-full flex items-center justify-center shrink-0',
                                            msg.role === 'user' ? 'bg-gray-200' : 'bg-brand-blue text-white'
                                        )}
                                    >
                                        {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
                                    </div>

                                    <div
                                        className={clsx(
                                            'py-3 px-4 rounded-2xl max-w-[80%] overflow-hidden',
                                            msg.role === 'user'
                                                ? 'bg-gray-100 text-gray-900 rounded-tr-sm'
                                                : 'bg-blue-50 text-slate-800 rounded-tl-sm'
                                        )}
                                    >
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
                            ))
                        )}
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
                                placeholder={
                                    currentConversationId
                                        ? 'Type your message...'
                                        : 'Create a conversation first...'
                                }
                                className="flex-1 bg-gray-50 border border-transparent focus:bg-white focus:border-brand-blue outline-none rounded-xl px-4 py-3 transition-all"
                                disabled={loading || !currentConversationId}
                            />
                            <button
                                type="submit"
                                disabled={loading || !input.trim() || !currentConversationId}
                                className="bg-brand-blue text-white p-3 rounded-xl hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                            >
                                <Send size={20} />
                            </button>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    );
}
