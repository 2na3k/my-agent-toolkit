import { useState } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Check, Copy } from 'lucide-react';

export function CodeBlock({ node, inline, className, children, ...props }: any) {
    const match = /language-(\w+)/.exec(className || '');
    const [copied, setCopied] = useState(false);

    // If it's inline code (single backtick)
    if (inline || !match) {
        return (
            <code className={`${className} bg-gray-200 text-red-500 rounded px-1 py-0.5 font-mono text-sm`} {...props}>
                {children}
            </code>
        );
    }

    const language = match[1];
    const value = String(children).replace(/\n$/, '');

    const handleCopy = () => {
        navigator.clipboard.writeText(value);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <div className="relative group rounded-xl overflow-hidden my-4 border border-gray-200 shadow-sm not-prose">
            <div className="flex items-center justify-between px-4 py-2 bg-[#282c34] text-gray-400 text-xs border-b border-gray-700/50">
                <span className="font-mono font-semibold text-gray-300">{language}</span>
                <button
                    onClick={handleCopy}
                    className="flex items-center gap-1.5 hover:text-white transition-colors p-1 rounded-md hover:bg-white/10"
                    title="Copy code"
                >
                    {copied ? (
                        <>
                            <Check size={14} className="text-green-400" />
                            <span className="text-green-400">Copied!</span>
                        </>
                    ) : (
                        <>
                            <Copy size={14} />
                            <span>Copy</span>
                        </>
                    )}
                </button>
            </div>
            <SyntaxHighlighter
                language={language}
                style={oneDark}
                customStyle={{
                    margin: 0,
                    borderRadius: '0 0 0.75rem 0.75rem',
                    padding: '1.5rem',
                    fontSize: '0.875rem',
                    lineHeight: '1.6',
                    background: '#282c34'
                }}
                showLineNumbers={true}
                wrapLines={true}
                {...props}
            >
                {value}
            </SyntaxHighlighter>
        </div>
    );
}
