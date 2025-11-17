/**
 * CodeSkeleton Component
 * Animated skeleton loader for code blocks
 */

import { VStack, Box, useColorModeValue } from '@chakra-ui/react';

interface CodeSkeletonProps {
  lines?: number;
}

export function CodeSkeleton({ lines = 10 }: CodeSkeletonProps) {
  const skeletonBg = useColorModeValue('gray.200', 'gray.700');

  // Generate random widths for realistic code appearance
  const lineWidths = Array.from({ length: lines }, () =>
    Math.random() * 30 + 70 // 70-100%
  );

  return (
    <VStack spacing={2} align="stretch" w="100%">
      {lineWidths.map((width, i) => (
        <Box
          key={i}
          h="16px"
          bg={skeletonBg}
          borderRadius="sm"
          w={`${width}%`}
          className="skeleton-shimmer"
        />
      ))}
    </VStack>
  );
}

export default CodeSkeleton;
