import { useEffect, useState } from 'react';
import { getTools, type ToolInfo } from '@/lib/api';
import { Wrench, AlertTriangle, CheckCircle, Tag, Layers, ChevronDown, ChevronUp } from 'lucide-react';
import clsx from 'clsx';

export default function Tools() {
    const [tools, setTools] = useState<ToolInfo[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [selectedCategory, setSelectedCategory] = useState<string>('all');
    const [expandedTools, setExpandedTools] = useState<Set<string>>(new Set());

    useEffect(() => {
        loadTools();
    }, []);

    const loadTools = async () => {
        try {
            setLoading(true);
            const data = await getTools();
            setTools(data);
        } catch (err) {
            setError('Failed to load tools');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const toggleExpanded = (toolName: string) => {
        const newExpanded = new Set(expandedTools);
        if (newExpanded.has(toolName)) {
            newExpanded.delete(toolName);
        } else {
            newExpanded.add(toolName);
        }
        setExpandedTools(newExpanded);
    };

    // Get unique categories
    const categories = ['all', ...new Set(tools.map(t => t.category))];

    // Filter tools by category
    const filteredTools = selectedCategory === 'all'
        ? tools
        : tools.filter(t => t.category === selectedCategory);

    // Group tools by category for stats
    const toolsByCategory = tools.reduce((acc, tool) => {
        acc[tool.category] = (acc[tool.category] || 0) + 1;
        return acc;
    }, {} as Record<string, number>);

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <div className="text-center">
                    <div className="w-8 h-8 border-4 border-brand-blue border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                    <p className="text-gray-500">Loading tools...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <div className="text-center text-red-500">
                    <AlertTriangle className="w-12 h-12 mx-auto mb-4" />
                    <p>{error}</p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-black">Tools</h1>
                    <p className="text-gray-500 mt-1">
                        Available tools for agents to interact with the system
                    </p>
                </div>
                <div className="flex items-center gap-4 text-sm">
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-green-500"></div>
                        <span className="text-gray-600">{tools.filter(t => !t.dangerous).length} Safe</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-red-500"></div>
                        <span className="text-gray-600">{tools.filter(t => t.dangerous).length} Dangerous</span>
                    </div>
                </div>
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-white rounded-xl p-4 border border-gray-100">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-brand-blue/10 flex items-center justify-center">
                            <Wrench className="w-5 h-5 text-brand-blue" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold text-black">{tools.length}</p>
                            <p className="text-sm text-gray-500">Total Tools</p>
                        </div>
                    </div>
                </div>

                <div className="bg-white rounded-xl p-4 border border-gray-100">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-green-500/10 flex items-center justify-center">
                            <CheckCircle className="w-5 h-5 text-green-500" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold text-black">{tools.filter(t => t.enabled).length}</p>
                            <p className="text-sm text-gray-500">Enabled</p>
                        </div>
                    </div>
                </div>

                <div className="bg-white rounded-xl p-4 border border-gray-100">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center">
                            <Layers className="w-5 h-5 text-purple-500" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold text-black">{categories.length - 1}</p>
                            <p className="text-sm text-gray-500">Categories</p>
                        </div>
                    </div>
                </div>

                <div className="bg-white rounded-xl p-4 border border-gray-100">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-red-500/10 flex items-center justify-center">
                            <AlertTriangle className="w-5 h-5 text-red-500" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold text-black">{tools.filter(t => t.dangerous).length}</p>
                            <p className="text-sm text-gray-500">Dangerous</p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Category Filter */}
            <div className="flex gap-2 overflow-x-auto pb-2">
                {categories.map(category => (
                    <button
                        key={category}
                        onClick={() => setSelectedCategory(category)}
                        className={clsx(
                            "px-4 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap",
                            selectedCategory === category
                                ? "bg-brand-blue text-white"
                                : "bg-white text-gray-600 hover:bg-gray-50 border border-gray-100"
                        )}
                    >
                        {category.charAt(0).toUpperCase() + category.slice(1)}
                        {category !== 'all' && (
                            <span className="ml-2 text-xs opacity-75">
                                ({toolsByCategory[category] || 0})
                            </span>
                        )}
                    </button>
                ))}
            </div>

            {/* Tools List */}
            <div className="space-y-3">
                {filteredTools.map(tool => {
                    const isExpanded = expandedTools.has(tool.name);

                    return (
                        <div
                            key={tool.name}
                            className="bg-white rounded-xl border border-gray-100 overflow-hidden transition-all hover:border-gray-200"
                        >
                            {/* Tool Header */}
                            <div
                                className="p-4 cursor-pointer"
                                onClick={() => toggleExpanded(tool.name)}
                            >
                                <div className="flex items-start justify-between gap-4">
                                    <div className="flex items-start gap-3 flex-1">
                                        {/* Icon */}
                                        <div className={clsx(
                                            "w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0",
                                            tool.dangerous
                                                ? "bg-red-500/10"
                                                : "bg-green-500/10"
                                        )}>
                                            {tool.dangerous ? (
                                                <AlertTriangle className="w-5 h-5 text-red-500" />
                                            ) : (
                                                <CheckCircle className="w-5 h-5 text-green-500" />
                                            )}
                                        </div>

                                        {/* Info */}
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2 mb-1">
                                                <h3 className="font-semibold text-black">{tool.name}</h3>
                                                <span className={clsx(
                                                    "px-2 py-0.5 rounded text-xs font-medium",
                                                    tool.dangerous
                                                        ? "bg-red-500/10 text-red-600"
                                                        : "bg-green-500/10 text-green-600"
                                                )}>
                                                    {tool.dangerous ? "Dangerous" : "Safe"}
                                                </span>
                                                <span className="px-2 py-0.5 rounded text-xs font-medium bg-purple-500/10 text-purple-600">
                                                    {tool.category}
                                                </span>
                                            </div>
                                            <p className="text-sm text-gray-600 mb-2">{tool.description}</p>

                                            {/* Tags */}
                                            <div className="flex flex-wrap gap-1.5">
                                                {tool.tags.map(tag => (
                                                    <span
                                                        key={tag}
                                                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-gray-100 text-xs text-gray-600"
                                                    >
                                                        <Tag className="w-3 h-3" />
                                                        {tag}
                                                    </span>
                                                ))}
                                            </div>
                                        </div>

                                        {/* Expand Icon */}
                                        <button className="p-1 hover:bg-gray-100 rounded transition-colors">
                                            {isExpanded ? (
                                                <ChevronUp className="w-5 h-5 text-gray-400" />
                                            ) : (
                                                <ChevronDown className="w-5 h-5 text-gray-400" />
                                            )}
                                        </button>
                                    </div>
                                </div>
                            </div>

                            {/* Tool Details (Expanded) */}
                            {isExpanded && (
                                <div className="border-t border-gray-100 p-4 bg-gray-50">
                                    <h4 className="font-semibold text-sm text-black mb-3">Parameters</h4>
                                    {tool.parameters.length === 0 ? (
                                        <p className="text-sm text-gray-500 italic">No parameters</p>
                                    ) : (
                                        <div className="space-y-3">
                                            {tool.parameters.map(param => (
                                                <div
                                                    key={param.name}
                                                    className="bg-white rounded-lg p-3 border border-gray-100"
                                                >
                                                    <div className="flex items-start justify-between gap-3">
                                                        <div className="flex-1">
                                                            <div className="flex items-center gap-2 mb-1">
                                                                <code className="text-sm font-mono font-semibold text-brand-blue">
                                                                    {param.name}
                                                                </code>
                                                                <span className="text-xs text-gray-500">
                                                                    ({param.type})
                                                                </span>
                                                                {param.required && (
                                                                    <span className="px-1.5 py-0.5 rounded text-xs font-medium bg-red-500/10 text-red-600">
                                                                        required
                                                                    </span>
                                                                )}
                                                            </div>
                                                            <p className="text-sm text-gray-600">{param.description}</p>
                                                            {param.default !== undefined && (
                                                                <p className="text-xs text-gray-500 mt-1">
                                                                    Default: <code className="font-mono">{JSON.stringify(param.default)}</code>
                                                                </p>
                                                            )}
                                                            {param.enum && (
                                                                <p className="text-xs text-gray-500 mt-1">
                                                                    Allowed: <code className="font-mono">{param.enum.join(', ')}</code>
                                                                </p>
                                                            )}
                                                        </div>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            {filteredTools.length === 0 && (
                <div className="text-center py-12 text-gray-500">
                    No tools found in this category
                </div>
            )}
        </div>
    );
}
