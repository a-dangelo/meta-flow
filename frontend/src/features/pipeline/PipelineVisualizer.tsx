/**
 * PipelineVisualizer Component
 * Shows the 5-stage agent generation pipeline with real-time progress
 */

import { useMemo } from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Progress,
  Badge,
  Flex,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Collapse,
  useColorModeValue,
} from '@chakra-ui/react';
import {
  CheckCircleIcon,
  TimeIcon,
  WarningIcon,
} from '@chakra-ui/icons';
import type { PipelineStage } from '@/types';

interface PipelineVisualizerProps {
  currentStage: PipelineStage;
  progress: number;
  error?: string | null;
  executionTime?: number;
}

interface StageConfig {
  id: Exclude<PipelineStage, 'idle' | 'error'>;
  label: string;
  description: string;
  icon?: React.ElementType;
}

/**
 * Pipeline stage configurations
 */
const STAGES: StageConfig[] = [
  {
    id: 'parsing',
    label: 'Parse Specification',
    description: 'Reading and validating input format',
  },
  {
    id: 'validating',
    label: 'Validate Structure',
    description: 'Checking workflow requirements',
  },
  {
    id: 'generating_json',
    label: 'Generate JSON',
    description: 'Creating structured workflow AST',
  },
  {
    id: 'generating_code',
    label: 'Generate Python',
    description: 'Converting AST to executable code',
  },
  {
    id: 'complete',
    label: 'Complete',
    description: 'Agent generated successfully',
    icon: CheckCircleIcon,
  },
];

/**
 * Get stage status based on current stage and progress
 */
function getStageStatus(
  stage: StageConfig,
  currentStage: PipelineStage,
  hasError: boolean
): 'pending' | 'active' | 'complete' | 'error' {
  const stageIndex = STAGES.findIndex((s) => s.id === stage.id);

  // Handle special cases first
  if (currentStage === 'idle') return 'pending';
  if (currentStage === 'error') {
    // If we're in error state, mark the current stage and all before it as error
    const errorStageIndex = STAGES.findIndex((s) => s.id === stage.id);
    return errorStageIndex !== -1 ? 'error' : 'pending';
  }

  // Find the current stage index, excluding 'idle' and 'error' which aren't in STAGES
  const currentIndex = STAGES.findIndex((s) => s.id === currentStage);

  if (hasError && currentStage === stage.id) return 'error';
  if (stageIndex < currentIndex) return 'complete';
  if (stageIndex === currentIndex) return 'active';
  return 'pending';
}

/**
 * Stage indicator component
 */
function StageIndicator({
  stage,
  status,
  isLast,
}: {
  stage: StageConfig;
  status: 'pending' | 'active' | 'complete' | 'error';
  isLast: boolean;
}) {
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  const statusColors = {
    pending: { bg: 'gray.100', border: 'gray.300', text: 'gray.500' },
    active: { bg: 'blue.50', border: 'blue.500', text: 'blue.700' },
    complete: { bg: 'green.50', border: 'green.500', text: 'green.700' },
    error: { bg: 'red.50', border: 'red.500', text: 'red.700' },
  };

  const colors = statusColors[status];

  return (
    <HStack spacing={3} align="start">
      <VStack spacing={2} align="center">
        {/* Stage circle */}
        <Box
          position="relative"
          w={10}
          h={10}
          borderRadius="full"
          bg={colors.bg}
          border="2px solid"
          borderColor={colors.border}
          display="flex"
          alignItems="center"
          justifyContent="center"
        >
          {status === 'complete' && <CheckCircleIcon color={colors.text} />}
          {status === 'active' && <TimeIcon color={colors.text} />}
          {status === 'error' && <WarningIcon color={colors.text} />}
          {status === 'pending' && (
            <Text fontSize="sm" fontWeight="bold" color={colors.text}>
              {STAGES.findIndex((s) => s.id === stage.id) + 1}
            </Text>
          )}
        </Box>

        {/* Connector line */}
        {!isLast && (
          <Box
            w="2px"
            h={16}
            bg={status === 'complete' ? colors.border : borderColor}
            opacity={status === 'pending' ? 0.3 : 1}
          />
        )}
      </VStack>

      {/* Stage details */}
      <VStack align="start" spacing={1} flex={1} pb={isLast ? 0 : 4}>
        <HStack>
          <Text
            fontWeight="bold"
            fontSize="sm"
            color={status === 'pending' ? 'gray.500' : colors.text}
          >
            {stage.label}
          </Text>
          {status === 'active' && (
            <Badge colorScheme="blue" variant="solid" fontSize="xs">
              IN PROGRESS
            </Badge>
          )}
        </HStack>
        <Text fontSize="xs" color="gray.600">
          {stage.description}
        </Text>
      </VStack>
    </HStack>
  );
}

/**
 * Main PipelineVisualizer component
 */
export function PipelineVisualizer({
  currentStage,
  progress,
  error,
  executionTime,
}: PipelineVisualizerProps) {
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  const hasError = currentStage === 'error' || !!error;

  // Calculate stage progress
  const stageProgress = useMemo(() => {
    if (currentStage === 'idle') return 0;
    if (currentStage === 'complete') return 100;
    if (currentStage === 'error') return 0;
    return progress;
  }, [currentStage, progress]);

  return (
    <VStack spacing={4} align="stretch">
      {/* Header */}
      <Flex justify="space-between" align="center">
        <Text fontSize="lg" fontWeight="bold">
          Generation Pipeline
        </Text>
        {executionTime && (
          <Badge colorScheme="gray" variant="outline">
            {(executionTime / 1000).toFixed(2)}s
          </Badge>
        )}
      </Flex>

      {/* Overall progress */}
      {currentStage !== 'idle' && (
        <Box>
          <Flex justify="space-between" mb={2}>
            <Text fontSize="sm" color="gray.600">
              Overall Progress
            </Text>
            <Text fontSize="sm" fontWeight="bold">
              {stageProgress}%
            </Text>
          </Flex>
          <Progress
            value={stageProgress}
            size="sm"
            colorScheme={hasError ? 'red' : currentStage === 'complete' ? 'green' : 'blue'}
            hasStripe={currentStage !== 'complete'}
            isAnimated={currentStage !== 'complete' && currentStage !== 'error'}
          />
        </Box>
      )}

      {/* Pipeline stages */}
      <Box
        bg={bgColor}
        border="1px solid"
        borderColor={borderColor}
        borderRadius="md"
        p={4}
      >
        <VStack spacing={0} align="stretch">
          {STAGES.map((stage, index) => (
            <StageIndicator
              key={stage.id}
              stage={stage}
              status={getStageStatus(stage, currentStage, hasError)}
              isLast={index === STAGES.length - 1}
            />
          ))}
        </VStack>
      </Box>

      {/* Error display */}
      <Collapse in={hasError && !!error}>
        <Alert status="error" borderRadius="md">
          <AlertIcon />
          <Box>
            <AlertTitle>Generation Failed</AlertTitle>
            <AlertDescription>
              <Text whiteSpace="pre-wrap">{error}</Text>
            </AlertDescription>
          </Box>
        </Alert>
      </Collapse>

      {/* Success message */}
      <Collapse in={currentStage === 'complete' && !hasError}>
        <Alert status="success" borderRadius="md">
          <AlertIcon />
          <Box>
            <AlertTitle>Agent Generated Successfully!</AlertTitle>
            <AlertDescription>
              Your agent has been generated and is ready to use.
              {executionTime && ` Generation took ${(executionTime / 1000).toFixed(2)} seconds.`}
            </AlertDescription>
          </Box>
        </Alert>
      </Collapse>
    </VStack>
  );
}

export default PipelineVisualizer;