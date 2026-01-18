import { useEffect, useState } from 'react';
import { getAgents, type AgentInfo } from '@/lib/api';
import { Link } from 'react-router-dom';
import { Bot, ArrowRight } from 'lucide-react';

export default function Dashboard() {
    const [agents, setAgents] = useState<AgentInfo[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        getAgents().then(data => {
            setAgents(data);
            setLoading(false);
        }).catch(err => {
            console.error(err);
            setLoading(false);
        });
    }, []);

    return (
        <div>
            <div className="mb-8">
                <h1 className="text-3xl font-bold mb-2">My Agents</h1>
                <p className="text-gray-500">Manage and interact with your AI agents.</p>
            </div>

            {loading ? (
                <div className="flex items-center justify-center h-64">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-blue"></div>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {agents.map(agent => (
                        <AgentCard key={agent.id} agent={agent} />
                    ))}

                    {/* Add New Agent Card */}
                    <button className="group relative flex flex-col items-center justify-center p-8 rounded-xl border-2 border-dashed border-gray-200 hover:border-brand-blue hover:bg-brand-blue/5 transition-all cursor-pointer text-center h-full min-h-[200px]">
                        <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center mb-4 shadow-sm group-hover:scale-110 transition-transform">
                            <span className="text-2xl font-light text-brand-blue">+</span>
                        </div>
                        <h3 className="font-semibold text-lg mb-1">Create New Agent</h3>
                        <p className="text-sm text-gray-500">Configure a new custom agent</p>
                    </button>
                </div>
            )}
        </div>
    );
}

function AgentCard({ agent }: { agent: AgentInfo }) {
    // Use a nice display name if possible, capitalize
    const displayName = agent.id.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');

    return (
        <Link to={`/agents/${agent.id}`} className="group block bg-white rounded-xl p-6 border border-gray-100 hover:shadow-lg hover:shadow-gray-200/50 hover:-translate-y-1 transition-all duration-300">
            <div className="flex items-start justify-between mb-4">
                <div className="w-12 h-12 rounded-xl bg-gray-50 flex items-center justify-center group-hover:bg-brand-blue group-hover:text-white transition-colors">
                    <Bot size={24} />
                </div>
                {agent.metadata?.enabled !== false && (
                    <span className="px-2 py-1 text-xs font-medium bg-green-50 text-green-600 rounded-full flex items-center gap-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
                        Active
                    </span>
                )}
            </div>

            <h3 className="font-bold text-xl mb-2 text-gray-900">{displayName}</h3>
            <p className="text-gray-500 text-sm mb-6 line-clamp-2 min-h-[40px]">
                {agent.description || "No description provided."}
            </p>

            <div className="flex items-center text-brand-blue font-medium text-sm group-hover:translate-x-1 transition-transform">
                Start Chat <ArrowRight size={16} className="ml-1" />
            </div>
        </Link>
    );
}
