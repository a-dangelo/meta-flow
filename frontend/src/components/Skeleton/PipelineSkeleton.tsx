/**
 * PipelineSkeleton Component
 * Animated skeleton loader for pipeline visualizer
 */

import { VStack, HStack, Box, useColorModeValue } from '@chakra-ui/react';

export function PipelineSkeleton() {
  const skeletonBg = useColorModeValue('gray.200', 'gray.700');
  const circleBg = useColorModeValue('gray.300', 'gray.600');

  return (
    <VStack spacing={6} align="stretch">
      {/* Progress bar skeleton */}
      <Box h="8px" bg={skeletonBg} borderRadius="full" className="skeleton-shimmer" />

      {/* Stage skeletons */}
      {[...Array(5)].map((_, i) => (
        <HStack key={i} spacing={4}>
          {/* Circle */}
          <Box
            w="40px"
            h="40px"
            borderRadius="full"
            bg={circleBg}
            flexShrink={0}
            className="skeleton-shimmer"
          />
          {/* Text */}
          <VStack align="stretch" flex={1} spacing={2}>
            <Box h="16px" bg={skeletonBg} borderRadius="sm" w="80%" className="skeleton-shimmer" />
            <Box h="12px" bg={skeletonBg} borderRadius="sm" w="60%" className="skeleton-shimmer" />
          </VStack>
        </HStack>
      ))}
    </VStack>
  );
}

export default PipelineSkeleton;
