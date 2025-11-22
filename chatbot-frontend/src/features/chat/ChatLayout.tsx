/**
 * Main chat layout component
 */

import React, { useState } from 'react';
import {
  Box,
  Flex,
  Container,
  Heading,
  Text,
  IconButton,
  Button,
  Badge,
  Drawer,
  DrawerOverlay,
  DrawerContent,
  useDisclosure,
} from '@chakra-ui/react';
import { MessageList } from './MessageList';
import { Composer } from './Composer';
import { ParameterDrawer } from './ParameterDrawer';
import { ExecutionPanel } from './ExecutionPanel';
import { useChat } from '../../hooks/useChat';

export const ChatLayout: React.FC = () => {
  const {
    session,
    messages,
    isLoading,
    error,
    isConnected,
    status,
    workflow,
    executionLogs,
    pendingParameters,
    sendMessage,
    startNewSession,
    clearSession,
    clearError,
  } = useChat();

  const { isOpen: isParamsOpen, onOpen: onOpenParams, onClose: onCloseParams } = useDisclosure();
  const { isOpen: isLogsOpen, onOpen: onOpenLogs, onClose: onCloseLogs } = useDisclosure();

  // Show parameter drawer when we have pending parameters
  React.useEffect(() => {
    if (pendingParameters.length > 0 && status === 'collecting_parameters') {
      onOpenParams();
    }
  }, [pendingParameters, status]);

  // Show execution panel when executing
  React.useEffect(() => {
    if (status === 'executing') {
      onOpenLogs();
    }
  }, [status]);

  return (
    <Flex h="100vh" bg="sand.100">
      {/* Main Chat Area */}
      <Container maxW="container.lg" p={0}>
        <Flex direction="column" h="100vh">
          {/* Header */}
          <Box
            bg="white"
            borderBottom="1px solid"
            borderColor="sand.200"
            p={4}
            boxShadow="sm"
          >
            <Flex justify="space-between" align="center">
              <Flex align="center" gap={3}>
                <Heading size="md" color="ocean.600">
                  Meta-Flow Assistant
                </Heading>
                {workflow && (
                  <Badge colorScheme="blue" fontSize="sm">
                    {workflow.name}
                  </Badge>
                )}
              </Flex>
              <Flex gap={2} align="center">
                {/* Connection Status */}
                <Badge
                  colorScheme={isConnected ? 'green' : 'gray'}
                  variant="subtle"
                  fontSize="xs"
                >
                  {isConnected ? '● Connected' : '○ Disconnected'}
                </Badge>

                {/* Status Badge */}
                {status && status !== 'pending' && (
                  <Badge colorScheme={getStatusColor(status)} variant="solid">
                    {getStatusLabel(status)}
                  </Badge>
                )}

                {/* Action Buttons */}
                {executionLogs.length > 0 && (
                  <Button size="sm" variant="ghost" onClick={onOpenLogs}>
                    View Logs ({executionLogs.length})
                  </Button>
                )}

                {pendingParameters.length > 0 && (
                  <Button size="sm" variant="outline" onClick={onOpenParams}>
                    Parameters ({pendingParameters.length})
                  </Button>
                )}

                <Button size="sm" variant="outline" onClick={startNewSession}>
                  New Chat
                </Button>
              </Flex>
            </Flex>
          </Box>

          {/* Message List */}
          <Box flex="1" overflowY="auto" bg="sand.50">
            <MessageList
              messages={messages}
              isLoading={isLoading}
              error={error}
              workflow={workflow}
            />
          </Box>

          {/* Composer */}
          <Box
            bg="white"
            borderTop="1px solid"
            borderColor="sand.200"
            p={4}
            boxShadow="sm"
          >
            <Composer
              onSendMessage={sendMessage}
              isLoading={isLoading}
              status={status}
              placeholder={getPlaceholder(status)}
            />
          </Box>
        </Flex>
      </Container>

      {/* Parameter Collection Drawer */}
      <ParameterDrawer
        isOpen={isParamsOpen}
        onClose={onCloseParams}
        parameters={workflow?.parameters || []}
        pendingParameters={pendingParameters}
        onSubmit={(values) => {
          const formattedMessage = Object.entries(values)
            .map(([key, value]) => `${key}: ${value}`)
            .join(', ');
          sendMessage(formattedMessage);
          onCloseParams();
        }}
      />

      {/* Execution Panel */}
      <Drawer
        isOpen={isLogsOpen}
        onClose={onCloseLogs}
        placement="right"
        size="md"
      >
        <DrawerOverlay />
        <DrawerContent>
          <ExecutionPanel
            logs={executionLogs}
            status={status}
            onClose={onCloseLogs}
          />
        </DrawerContent>
      </Drawer>
    </Flex>
  );
};

// Helper functions
function getStatusColor(status: string): string {
  switch (status) {
    case 'completed':
      return 'green';
    case 'failed':
      return 'red';
    case 'executing':
      return 'blue';
    case 'collecting_parameters':
    case 'awaiting_user_input':
      return 'orange';
    default:
      return 'gray';
  }
}

function getStatusLabel(status: string): string {
  switch (status) {
    case 'collecting_parameters':
      return 'Collecting Info';
    case 'awaiting_user_input':
      return 'Waiting for Input';
    case 'ready_to_validate':
      return 'Validating';
    case 'executing':
      return 'Running';
    case 'completed':
      return 'Complete';
    case 'failed':
      return 'Failed';
    default:
      return status;
  }
}

function getPlaceholder(status: string): string {
  switch (status) {
    case 'collecting_parameters':
      return 'Provide the requested information...';
    case 'awaiting_user_input':
      return 'Enter your response...';
    case 'executing':
      return 'Workflow is executing...';
    case 'completed':
      return 'Start a new workflow or ask a question...';
    default:
      return 'Describe what you need help with...';
  }
}