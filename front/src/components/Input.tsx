import { useRef, useEffect } from 'react';
import SendButton from './SendButton';
import { useChat } from '../hooks/useChat';

interface InputProps {
  value: string;
  onChange: (value: string) => void;
  onKeyPress: (event: React.KeyboardEvent<HTMLTextAreaElement>) => void;
}

function Input({ value, onChange, onKeyPress }: InputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleInputChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    onChange(event.target.value);
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    onKeyPress(event);

    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      return;
    }
  };

  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = textarea.scrollHeight + "px";
    }
  }, [value]);

  return (
    <div className="flex flex-col gap-2 w-full">
      <textarea
        ref={textareaRef}
        className="w-full p-2 rounded-md outline-none focus:outline-none overflow-hidden resize-none"
        placeholder="Pergunte qualquer coisa..."
        rows={1}
        value={value}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
      />
    </div>
  );
}


interface ChatInputProps {
  centered?: boolean;
}

export default function ChatInput({ centered = false }: ChatInputProps) {
  const { inputValue, setInputValue, sendMessage } = useChat();

  const handleSendMessage = () => {
    sendMessage(inputValue);
  };

  const handleKeyPress = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSendMessage();
    }
  };

  const inputContent = (
    <div className="bg-[#303030] p-2 rounded-2xl flex flex-row">
      <Input
        value={inputValue}
        onChange={setInputValue}
        onKeyPress={handleKeyPress}
      />
      <div className="flex justify-end mt-0">
        <SendButton
          onClick={handleSendMessage}
          disabled={!inputValue.trim()}
        />
      </div>
    </div>
  );

  if (centered) {
    return inputContent;
  }

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-black/80 backdrop-blur-sm z-15">
      <div className="w-full max-w-4xl mx-auto p-4">
        {inputContent}
      </div>
    </div>
  );
}