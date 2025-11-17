/**
 * EmptyState Component
 * Placeholder for no data states
 */

import { VStack, Heading, Text, Box, useColorModeValue } from '@chakra-ui/react';
import { InfoIcon } from '@chakra-ui/icons';

interface EmptyStateProps {
  title: string;
  message: string;
  icon?: React.ReactElement;
}

export function EmptyState({ title, message, icon }: EmptyStateProps) {
  const iconColor = useColorModeValue('gray.400', 'gray.500');
  const textColor = useColorModeValue('gray.600', 'gray.400');

  return (
    <VStack spacing={6} py={12} px={6} textAlign="center">
      {/* Icon */}
      <Box
        w="80px"
        h="80px"
        borderRadius="full"
        bg={useColorModeValue('gray.100', 'gray.700')}
        display="flex"
        alignItems="center"
        justifyContent="center"
        animation="fadeIn 0.3s ease-in-out"
      >
        {icon || <InfoIcon boxSize="40px" color={iconColor} />}
      </Box>

      {/* Message */}
      <VStack spacing={2}>
        <Heading size="md" fontWeight="600">
          {title}
        </Heading>
        <Text color={textColor} maxW="400px" fontSize="sm">
          {message}
        </Text>
      </VStack>
    </VStack>
  );
}

export default EmptyState;
