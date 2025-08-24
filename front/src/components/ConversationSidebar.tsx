import { useChatContext } from '../contexts/ChatContext';
import { useConversations } from '../hooks/useConversations';
import SidebarToggle from './SidebarToggle';
import ConversationList, { type ConversationInfo } from './ConversationList';

interface ConversationSidebarProps {
  conversations: ConversationInfo[];
  currentConversationId: string | null;
  onSelectConversation: (conversationId: string) => void;
  onNewConversation: () => void;
  onDeleteConversation: (conversationId: string) => void;
  onRefreshConversations: () => void;
  onClose: () => void;
  showSidebar: boolean;
}

function ConversationSidebar({
  conversations,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  onRefreshConversations,
  onClose,
  showSidebar
}: ConversationSidebarProps) {

  return (
    <>
      {/* Mobile backdrop overlay */}
      <div 
        className={`lg:hidden fixed inset-0 bg-black/50 backdrop-blur-sm z-40 transition-opacity duration-300 ease-in-out ${
          showSidebar ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        }`}
        onClick={onClose}
      />
      
      {/* Sidebar */}
      <div className={`
        h-full border-r border-gray-700 flex flex-col z-50 fixed top-0 left-0
        transition-all duration-300 ease-in-out
        ${showSidebar ? 'w-80 translate-x-0' : 'w-16 -translate-x-0'}
        lg:translate-x-0
        bg-gray-900
      `}>
        {/* Header */}
                 <div className={`p-4 flex items-center transition-all duration-300 ease-in-out ${
           showSidebar ? 'justify-between border-b border-gray-700' : 'justify-center'
         }`}>
          <h2 className={`text-lg font-semibold text-white transition-all duration-300 ease-in-out ${
            showSidebar ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-4 pointer-events-none absolute'
          }`}>
            Conversas
          </h2>
          
          {showSidebar ? (
            <div className="flex gap-2">
              <button
                onClick={onNewConversation}
                className="p-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-white transition-colors duration-200"
                title="Nova conversa"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
              </button>
              <SidebarToggle />
              <button
                onClick={onClose}
                className="p-2 hover:bg-gray-700 rounded-lg text-gray-400 transition-colors duration-200 lg:hidden"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          ) : (
            <SidebarToggle />
          )}
        </div>

        {/* Body */}
        <div className={`flex-1 overflow-hidden transition-all duration-300 ease-in-out delay-75 ${
          showSidebar ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-4'
        }`}>
          <ConversationList
            conversations={conversations}
            currentConversationId={currentConversationId}
            onSelectConversation={onSelectConversation}
            onNewConversation={onNewConversation}
            onDeleteConversation={onDeleteConversation}
            onRefreshConversations={onRefreshConversations}
            show={showSidebar}
          />
        </div>

        {/* Footer */}
        <div className={`p-4 border-t border-gray-700 transition-all duration-300 ease-in-out delay-100 ${
          showSidebar ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4 pointer-events-none'
        }`}>
          <div className="text-xs text-gray-500 text-center">
            {conversations.length} conversa{conversations.length !== 1 ? 's' : ''}
          </div>
        </div>
      </div>
    </>
  );
}

export default function ChatSidebar() {
  const { state, dispatch } = useChatContext();
  const {
    conversations,
    currentConversationId,
    createNewConversation,
    deleteConversation,
    switchConversation,
    loadUserConversations,
  } = useConversations();

  return (
    <ConversationSidebar
      conversations={conversations}
      currentConversationId={currentConversationId}
      onSelectConversation={switchConversation}
      onNewConversation={createNewConversation}
      onDeleteConversation={deleteConversation}
      onRefreshConversations={loadUserConversations}
      onClose={() => dispatch({ type: 'SET_SHOW_SIDEBAR', payload: false })}
      showSidebar={state.showSidebar}
    />
  );
}