/**
 * ErrorState Component
 * Friendly error UI with actionable suggestions
 */

import { VStack, Heading, Text, Button, Box, useColorModeValue } from '@chakra-ui/react';
import { WarningIcon, RepeatIcon } from '@chakra-ui/icons';

interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  suggestion?: string;
}

export function ErrorState({
  title = 'Something went wrong',
  message,
  onRetry,
  suggestion,
}: ErrorStateProps) {
  const iconColor = useColorModeValue('red.500', 'red.300');
  const textColor = useColorModeValue('gray.600', 'gray.400');

  return (
    <VStack spacing={6} py={12} px={6} textAlign="center">
      {/* Error Icon */}
      <Box
        w="80px"
        h="80px"
        borderRadius="full"
        bg={useColorModeValue('red.50', 'red.900')}
        display="flex"
        alignItems="center"
        justifyContent="center"
        animation="shake 0.5s ease-in-out"
      >
        <WarningIcon boxSize="40px" color={iconColor} />
      </Box>

      {/* Error Message */}
      <VStack spacing={3}>
        <Heading size="lg" fontWeight="700">
          {title}
        </Heading>
        <Text color={textColor} maxW="500px" lineHeight="tall">
          {message}
        </Text>
        {suggestion && (
          <Text fontSize="sm" color={textColor} fontStyle="italic" maxW="500px">
            💡 {suggestion}
          </Text>
        )}
      </VStack>

      {/* Retry Button */}
      {onRetry && (
        <Button
          leftIcon={<RepeatIcon />}
          colorScheme="blue"
          size="lg"
          onClick={onRetry}
          _hover={{ transform: 'scale(1.05)' }}
          transition="all 0.2s"
        >
          Try Again
        </Button>
      )}
    </VStack>
  );
}

export default ErrorState;
