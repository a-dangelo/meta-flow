/**
 * Message composer component
 */

import React, { useState, useRef, KeyboardEvent } from 'react';
import {
  Box,
  Flex,
  Input,
  IconButton,
  Button,
  Textarea,
} from '@chakra-ui/react';

interface ComposerProps {
  onSendMessage: (message: string) => void;
  isLoading: boolean;
  status?: string;
  placeholder?: string;
}

export const Composer: React.FC<ComposerProps> = ({
  onSendMessage,
  isLoading,
  status,
  placeholder = 'Type your message...',
}) => {
  const [message, setMessage] = useState('');
  const [isMultiline, setIsMultiline] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    const trimmed = message.trim();
    if (!trimmed || isLoading) return;

    onSendMessage(trimmed);
    setMessage('');
    setIsMultiline(false);
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    // Send on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
    // Add new line on Shift+Enter
    else if (e.key === 'Enter' && e.shiftKey) {
      setIsMultiline(true);
    }
  };

  const isDisabled = isLoading || status === 'executing' || status === 'completed';

  return (
    <Flex gap={3} align="flex-end">
      {isMultiline ? (
        <Textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={isDisabled}
          minH="44px"
          maxH="120px"
          resize="none"
          borderRadius="lg"
          bg="white"
          borderColor="sand.300"
          _hover={{ borderColor: 'ocean.400' }}
          _focus={{
            borderColor: 'ocean.500',
            boxShadow: '0 0 0 1px rgba(31, 111, 139, 0.2)',
          }}
          flex="1"
        />
      ) : (
        <Input
          value={message}
          onChange={(e) => {
            setMessage(e.target.value);
            // Switch to multiline if message contains newlines
            if (e.target.value.includes('\n')) {
              setIsMultiline(true);
            }
          }}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={isDisabled}
          size="lg"
          borderRadius="lg"
          bg="white"
          borderColor="sand.300"
          _hover={{ borderColor: 'ocean.400' }}
          _focus={{
            borderColor: 'ocean.500',
            boxShadow: '0 0 0 1px rgba(31, 111, 139, 0.2)',
          }}
          flex="1"
        />
      )}

      <Button
        onClick={handleSend}
        isLoading={isLoading}
        isDisabled={!message.trim() || isDisabled}
        colorScheme="blue"
        size="lg"
        borderRadius="lg"
        px={6}
        bg="ocean.500"
        _hover={{ bg: 'ocean.600' }}
      >
        Send
      </Button>
    </Flex>
  );
};