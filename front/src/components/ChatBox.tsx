import { useEffect } from 'react';
import { ChatProvider } from '../contexts/ChatContext';
import { useConversations } from '../hooks/useConversations';
import { useChat } from '../hooks/useChat';
import { useChatContext } from '../contexts/ChatContext';
import { getCookie } from '../utils/cookies';
import ChatSidebar from './ConversationSidebar';
import ChatInput from './Input';
import Conversation from './Conversation';  

function ChatBoxContent() {
  const { loadUserConversations, loadConversationHistory } = useConversations();
  const { messages } = useChat();
  const { state } = useChatContext();

  useEffect(() => {
    const currentConversation = state.conversations.find(
      conv => conv.conversation_id === state.currentConversationId
    );
    
    if (currentConversation && currentConversation.title !== 'Nova Conversa') {
      document.title = currentConversation.title;
    } else {
      document.title = 'Infinite Chat';
    }
  }, [state.currentConversationId, state.conversations]);

  useEffect(() => {
    loadUserConversations();

    const conversationId = getCookie('conversation_id');
    if (conversationId) {
      loadConversationHistory(conversationId);
    }
  }, [loadUserConversations, loadConversationHistory]);

  return (
    <div className="flex h-screen w-full mx-auto">
      <ChatSidebar />
      
      <div className="flex flex-col flex-1 min-h-screen max-w-4xl mx-auto relative">
        {messages.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center p-4">
            <div className="text-center mb-8">
              <div className="text-lg mb-2 text-gray-400">👋 Bem-vindo ao Infinite Chat!</div>
              <div className="text-sm text-gray-500">Pergunte qualquer coisa sobre a InfinitePay ou Matemática.</div>
            </div>
            <div className="w-full max-w-2xl">
              <ChatInput centered={true} />
            </div>
          </div>
        ) : (
          <>
            <div className="flex-1 pb-20 pt-5">
              <Conversation messages={messages} />
            </div>
            <ChatInput />
          </>
        )}
      </div>
    </div>
  );
}

export default function ChatBox() {
  return (
    <ChatProvider>
      <ChatBoxContent />
    </ChatProvider>
  );
}