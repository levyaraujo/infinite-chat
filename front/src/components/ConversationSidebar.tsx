import { useEffect } from 'react';
import { useChatContext } from '../contexts/ChatContext';
import { useConversations } from '../hooks/useConversations';
import SidebarToggle from './SidebarToggle';
import ConversationList from './ConversationList';

export default function ConversationSidebar() {
  const { state, dispatch } = useChatContext();
  const {
    conversations,
    currentConversationId,
    createNewConversation,
    deleteConversation,
    switchConversation,
    loadUserConversations,
  } = useConversations();

  const { showSidebar } = state;
  
  useEffect(() => {
    const isMobile = window.innerWidth < 768;
    document.body.style.overflow = (showSidebar && isMobile) ? 'hidden' : 'unset';
    
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [showSidebar]);

  const closeSidebar = () => dispatch({ type: 'SET_SHOW_SIDEBAR', payload: false });
  
  const handleAction = (action: () => void) => {
    action();
    if (window.innerWidth < 768) closeSidebar();
  };

  return (
    <>
      {!showSidebar && (
        <div className="md:hidden fixed top-4 left-4 z-50">
          <SidebarToggle />
        </div>
      )}

      {showSidebar && (
        <div className="fixed inset-0 z-40" onClick={closeSidebar} />
      )}

      <div className={`
        fixed top-0 left-0 h-screen z-50 flex flex-col bg-gray-900 border-r border-gray-700
        transition-transform duration-300 ease-in-out
        ${showSidebar 
          ? 'w-4/5 md:w-80 translate-x-0 ' 
          : 'w-80 -translate-x-full md:translate-x-0 md:w-16'
        }
      `}>
        
        {/* Header */}
        <div className={`p-4 flex items-center ${
          showSidebar ? 'justify-between border-b border-gray-700' : 'justify-center'
        }`}>
          {showSidebar && <h2 className="text-lg font-semibold text-white">Conversas</h2>}
          
          <div className="flex gap-2">
            {showSidebar && (
              <button
                onClick={() => handleAction(createNewConversation)}
                className="p-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-white transition-colors"
                title="Nova conversa"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
              </button>
            )}
            <SidebarToggle />
          </div>
        </div>

        {/* Body */}
        {showSidebar && (
          <div className="flex-1 min-h-0">
            <ConversationList
              conversations={conversations}
              currentConversationId={currentConversationId}
              onSelectConversation={(id) => handleAction(() => switchConversation(id))}
              onNewConversation={() => handleAction(createNewConversation)}
              onDeleteConversation={deleteConversation}
              onRefreshConversations={loadUserConversations}
              show={showSidebar}
            />
          </div>
        )}

        {/* Footer */}
        {showSidebar && (
          <div className="p-4 border-t border-gray-700 text-xs text-gray-500 text-center">
            {conversations.length} conversa{conversations.length !== 1 ? 's' : ''}
          </div>
        )}
      </div>
    </>
  );
}