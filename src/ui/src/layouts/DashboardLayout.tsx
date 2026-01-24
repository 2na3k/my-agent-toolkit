import { Link, Outlet, useLocation } from 'react-router-dom';
import { MessageSquare, Bot, Settings, Search, ChevronLeft, Menu } from 'lucide-react';
import clsx from 'clsx';
import { useState } from 'react';

export function DashboardLayout() {
    const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

    return (
        <div className="flex h-screen bg-[#F5F5F7] text-[#0A0B0D] relative">
            {/* Collapsed Sidebar Toggle Button */}
            {isSidebarCollapsed && (
                <button
                    onClick={() => setIsSidebarCollapsed(false)}
                    className="fixed left-4 top-4 z-50 bg-brand-blue text-white p-2.5 rounded-lg hover:bg-blue-600 transition-colors shadow-lg"
                    title="Show sidebar"
                >
                    <Menu size={20} />
                </button>
            )}

            <Sidebar isCollapsed={isSidebarCollapsed} onToggle={setIsSidebarCollapsed} />
            <main className="flex-1 overflow-auto">
                <div className="max-w-[1200px] mx-auto p-4 md:p-8">
                    <Outlet />
                </div>
            </main>
        </div>
    );
}

function Sidebar({ isCollapsed, onToggle }: { isCollapsed: boolean; onToggle: (collapsed: boolean) => void }) {
    const location = useLocation();

    const navItems = [
        { icon: MessageSquare, label: 'Chat', path: '/' },
        { icon: Bot, label: 'Agents', path: '/agents' },
        { icon: Settings, label: 'Settings', path: '/settings' },
    ];

    return (
        <div
            style={{
                width: isCollapsed ? '0px' : '280px',
                opacity: isCollapsed ? 0 : 1,
            }}
            className={clsx(
                "bg-white border-r border-gray-100 flex flex-col p-6 sticky top-0 h-screen transition-all duration-300 overflow-hidden",
                isCollapsed && "border-0 p-0"
            )}
        >
            {!isCollapsed && (
                <>
                    <div className="mb-10 px-2 flex items-center gap-3">
                        <div className="w-8 h-8 bg-brand-blue rounded-full flex items-center justify-center">
                            <svg viewBox="0 0 24 24" fill="none" className="w-5 h-5 text-white" stroke="currentColor" strokeWidth="3">
                                <circle cx="12" cy="12" r="10" />
                            </svg>
                        </div>
                        <span className="font-bold text-xl tracking-tight text-black">Agent Toolkit</span>
                    </div>

                    <div className="mb-6 relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                        <input
                            type="text"
                            placeholder="Search..."
                            className="w-full bg-gray-50 border border-transparent focus:bg-white focus:border-brand-blue outline-none rounded-lg py-2 pl-9 pr-3 text-sm transition-all"
                        />
                    </div>

                    <nav className="space-y-1">
                        {navItems.map((item) => {
                            const isActive = location.pathname === item.path || (item.path !== '/' && location.pathname.startsWith(item.path));
                            return (
                                <Link
                                    key={item.path}
                                    to={item.path}
                                    className={clsx(
                                        "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200",
                                        isActive
                                            ? "bg-gray-100/80 text-black"
                                            : "text-gray-500 hover:bg-gray-50 hover:text-black"
                                    )}
                                >
                                    <item.icon size={20} strokeWidth={isActive ? 2.5 : 2} className={isActive ? "text-brand-blue" : "text-gray-400"} />
                                    {item.label}
                                </Link>
                            );
                        })}
                    </nav>

                    <div className="mt-auto pt-6 border-t border-gray-100 flex items-center justify-between">
                        <div className="flex items-center gap-3 px-3">
                            <div className="w-8 h-8 rounded-full bg-gray-200" />
                            <div className="text-sm">
                                <div className="font-medium">User</div>
                                <div className="text-xs text-gray-400">Workspace</div>
                            </div>
                        </div>
                        <button
                            onClick={() => onToggle(true)}
                            className="p-1.5 hover:bg-gray-100 rounded-lg text-gray-600 hover:text-brand-blue transition-colors"
                            title="Hide sidebar"
                        >
                            <ChevronLeft size={18} />
                        </button>
                    </div>
                </>
            )}
        </div>
    );
}
