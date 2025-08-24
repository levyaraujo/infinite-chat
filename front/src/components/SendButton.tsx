import SendIcon from './SendIcon';

interface ButtonProps {
    onClick: () => void;
    disabled?: boolean;
}

export default function SendButton({ onClick, disabled }: ButtonProps) {
    return (
        <button
            className="bg-[#9AD50D] hover:bg-gradient-to-r hover:from-[#39E51E] hover:to-[#9AD50D] text-white px-4 py-3 transition-colors 
            duration-200 font-medium disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer 
            w-auto rounded-full flex items-center justify-center p-2 text-sm max-w-15 max-h-10"
            onClick={onClick}
            disabled={disabled}
        >
            <SendIcon />
        </button>
    )
}