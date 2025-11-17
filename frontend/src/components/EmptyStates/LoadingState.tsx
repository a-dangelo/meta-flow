/**
 * LoadingState Component
 * Unified loading component with optional message
 */

import { VStack, Text, Box, useColorModeValue } from '@chakra-ui/react';

interface LoadingStateProps {
  message?: string;
  submessage?: string;
}

export function LoadingState({
  message = 'Loading...',
  submessage,
}: LoadingStateProps) {
  const textColor = useColorModeValue('gray.600', 'gray.400');
  const spinnerBorder = useColorModeValue('blue.100', 'blue.900');
  const spinnerTop = useColorModeValue('blue.500', 'blue.300');

  return (
    <VStack spacing={4} py={12} textAlign="center">
      {/* Spinner */}
      <Box
        width="60px"
        height="60px"
        borderRadius="full"
        border="4px solid"
        borderColor={spinnerBorder}
        borderTopColor={spinnerTop}
        animation="spin 1s linear infinite"
      />

      {/* Message */}
      <VStack spacing={2}>
        <Text
          color={textColor}
          fontWeight="500"
          animation="pulse 2s ease-in-out infinite"
        >
          {message}
        </Text>
        {submessage && (
          <Text fontSize="sm" color={textColor}>
            {submessage}
          </Text>
        )}
      </VStack>
    </VStack>
  );
}

export default LoadingState;
