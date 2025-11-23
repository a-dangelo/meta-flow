/**
 * Message list component
 */

import React, { useRef, useEffect } from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Avatar,
  Badge,
  Card,
  CardBody,
  Spinner,
  Alert,
  AlertIcon,
  AlertDescription,
  Flex,
} from '@chakra-ui/react';
import type { ChatMessage, Workflow } from '../../services/types';

interface MessageListProps {
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  workflow?: Workflow;
}

export const MessageList: React.FC<MessageListProps> = ({
  messages,
  isLoading,
  error,
  workflow,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <VStack spacing={4} align="stretch" p={6}>
      {/* Welcome message if no messages */}
      {messages.length === 0 && !isLoading && (
        <Box textAlign="center" py={12}>
          <Text fontSize="lg" color="gray.500">
            👋 Welcome! Describe what you need help with.
          </Text>
          <Text fontSize="sm" color="gray.400" mt={2}>
            I can help you with expense reports, leave requests, IT tickets, and more.
          </Text>
        </Box>
      )}

      {/* Messages */}
      {messages.map((message, index) => (
        <MessageBubble
          key={index}
          message={message}
          workflow={message.confidence ? workflow : undefined}
        />
      ))}

      {/* Loading indicator */}
      {isLoading && (
        <HStack spacing={2} p={3}>
          <Spinner size="sm" color="ocean.500" />
          <Text fontSize="sm" color="gray.500">
            Processing your request...
          </Text>
        </HStack>
      )}

      {/* Error message */}
      {error && (
        <Alert status="error" borderRadius="lg">
          <AlertIcon />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Scroll anchor */}
      <div ref={bottomRef} />
    </VStack>
  );
};

interface MessageBubbleProps {
  message: ChatMessage;
  workflow?: Workflow;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message, workflow }) => {
  const isUser = message.role === 'user';

  return (
    <Flex justify={isUser ? 'flex-end' : 'flex-start'}>
      <HStack
        align="flex-start"
        spacing={3}
        maxW="70%"
        flexDirection={isUser ? 'row-reverse' : 'row'}
      >
        <Avatar
          size="sm"
          name={isUser ? 'You' : 'Assistant'}
          bg={isUser ? 'ocean.500' : 'sage.500'}
          color="white"
        />
        <Card
          bg={isUser ? 'ocean.500' : 'white'}
          color={isUser ? 'white' : 'gray.800'}
          boxShadow="sm"
          borderRadius="xl"
          borderTopRightRadius={isUser ? 'md' : 'xl'}
          borderTopLeftRadius={!isUser ? 'md' : 'xl'}
        >
          <CardBody py={3} px={4}>
            {/* Confidence badge for assistant messages */}
            {!isUser && message.confidence && workflow && (
              <HStack spacing={2} mb={2}>
                {(() => {
                  const percent = Math.round(message.confidence * 100);
                  const colorScheme = percent >= 70 ? 'green' : 'orange';
                  return (
                    <>
                      <Badge
                        colorScheme={colorScheme}
                        fontSize="xs"
                      >
                        {percent}% match
                      </Badge>
                      <Text fontSize="xs" color="gray.500">
                        {workflow.name}
                      </Text>
                    </>
                  );
                })()}
              </HStack>
            )}

            {/* Message content */}
            <Text
              fontSize="md"
              whiteSpace="pre-wrap"
              dangerouslySetInnerHTML={{
                __html: formatMessage(message.content),
              }}
            />

            {/* Timestamp */}
            {message.timestamp && (
              <Text
                fontSize="xs"
                color={isUser ? 'whiteAlpha.700' : 'gray.400'}
                mt={2}
              >
                {formatTime(message.timestamp)}
              </Text>
            )}
          </CardBody>
        </Card>
      </HStack>
    </Flex>
  );
};

// Helper functions
function formatMessage(content: string): string {
  // Convert markdown-style formatting to HTML
  let formatted = content
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br />');

  // Convert bullet points
  formatted = formatted.replace(/^[•·] (.+)$/gm, '• $1');

  return formatted;
}

function formatTime(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now.getTime() - date.getTime();

  // If today, show time only
  if (diff < 24 * 60 * 60 * 1000) {
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  // Otherwise show date and time
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}
