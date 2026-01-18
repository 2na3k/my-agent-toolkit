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


                </div>
            )}
        </div>
    );
}

function AgentCard({ agent }: { agent: AgentInfo }) {
    // Use a nice display name if possible, capitalize
    const displayName = agent.id.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');

    return (
        <Link to={`/agents/${agent.id}`} className="group block bg-white rounded-xl p-6 border border-gray-100 hover:border-brand-blue hover:bg-brand-blue hover:shadow-xl hover:shadow-brand-blue/20 hover:-translate-y-1 transition-all duration-300">
            <div className="flex items-start justify-between mb-4">
                <div className="w-12 h-12 rounded-xl bg-gray-50 flex items-center justify-center text-brand-blue group-hover:bg-white group-hover:text-brand-blue transition-colors">
                    <Bot size={24} />
                </div>
                {agent.metadata?.enabled !== false && (
                    <span className="px-2 py-1 text-xs font-medium bg-green-50 text-green-600 group-hover:bg-white/20 group-hover:text-white rounded-full flex items-center gap-1 transition-colors">
                        <span className="w-1.5 h-1.5 rounded-full bg-green-500 group-hover:bg-white" />
                        Active
                    </span>
                )}
            </div>

            <h3 className="font-bold text-xl mb-2 text-gray-900 group-hover:text-white transition-colors">{displayName}</h3>
            <p className="text-gray-500 text-sm mb-6 line-clamp-2 min-h-[40px] group-hover:text-blue-50 transition-colors">
                {agent.description || "No description provided."}
            </p>

            <div className="flex items-center text-brand-blue font-medium text-sm opacity-0 translate-y-2 group-hover:opacity-100 group-hover:translate-y-0 group-hover:text-white transition-all duration-300">
                Start Chat <ArrowRight size={16} className="ml-1" />
            </div>
        </Link>
    );
}
