import { useCallback } from 'react';
import { useChatContext } from '../contexts/ChatContext';
import { setCookie } from '../utils/cookies';
import { API_URL } from '../utils/urls';

export function useConversations() {
  const { state, dispatch } = useChatContext();

  const loadUserConversations = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/conversations`, {
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();
        dispatch({ type: 'SET_CONVERSATIONS', payload: data.conversations });
      }
    } catch (error) {
      console.error('Error loading conversations:', error);
    }
  }, [dispatch]);

  const loadConversationHistory = useCallback(async (conversationId: string) => {
    dispatch({ type: 'SET_LOADING_HISTORY', payload: true });
    try {
      const response = await fetch(
        `${API_URL}/conversations/${conversationId}/history?limit=50`,
        { credentials: 'include' }
      );

      if (response.ok) {
        const data = await response.json();
        const historyMessages = data.messages.map((msg: any) => ({
          id: msg.id,
          content: msg.content,
          sender: msg.sender,
          timestamp: new Date(msg.timestamp),
          agent: msg.agent,
          metadata: msg.metadata
        }));

        dispatch({ type: 'SET_MESSAGES', payload: historyMessages });
        dispatch({ type: 'SET_CURRENT_CONVERSATION_ID', payload: conversationId });
      }
    } catch (error) {
      console.error('Error loading conversation history:', error);
    } finally {
      dispatch({ type: 'SET_LOADING_HISTORY', payload: false });
    }
  }, [dispatch]);

  const createNewConversation = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/conversations`, {
        method: 'POST',
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();
        dispatch({ type: 'SET_CURRENT_CONVERSATION_ID', payload: data.conversation_id });
        dispatch({ type: 'RESET_MESSAGES' });
        loadUserConversations();
      }
    } catch (error) {
      console.error('Error creating new conversation:', error);
    }
  }, [dispatch, loadUserConversations]);

  const deleteConversation = useCallback(async (conversationId: string) => {
    try {
      const response = await fetch(`${API_URL}/conversations/${conversationId}`, {
        method: 'DELETE',
        credentials: 'include'
      });

      if (response.ok) {
        if (conversationId === state.currentConversationId) {
          await createNewConversation();
        }
        loadUserConversations();
      }
    } catch (error) {
      console.error('Error deleting conversation:', error);
    }
  }, [state.currentConversationId, createNewConversation, loadUserConversations]);

  const switchConversation = useCallback(async (conversationId: string) => {
    if (conversationId === state.currentConversationId) return;

    setCookie('conversation_id', conversationId);
    await loadConversationHistory(conversationId);
    dispatch({ type: 'SET_SHOW_SIDEBAR', payload: false });
  }, [state.currentConversationId, loadConversationHistory, dispatch]);

  return {
    conversations: state.conversations,
    currentConversationId: state.currentConversationId,
    isLoadingHistory: state.isLoadingHistory,
    loadUserConversations,
    loadConversationHistory,
    createNewConversation,
    deleteConversation,
    switchConversation,
  };
}