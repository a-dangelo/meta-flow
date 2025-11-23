/**
 * Execution details component showing generated code and results
 */

import React from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Badge,
  Button,
  Divider,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
  Code,
  useToast,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
} from '@chakra-ui/react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface ExecutionDetailsProps {
  status: string;
  pythonCode?: string;
  executionResult?: any;
  collectedParameters?: Record<string, any>;
  workflowName?: string;
}

export const ExecutionDetails: React.FC<ExecutionDetailsProps> = ({
  status,
  pythonCode,
  executionResult,
  collectedParameters,
  workflowName,
}) => {
  const toast = useToast();
  // Only show when workflow is completed
  if (status !== 'completed' || !executionResult) {
    return null;
  }

  const handleCopyCode = () => {
    if (pythonCode) {
      navigator.clipboard.writeText(pythonCode);
      toast({
        title: 'Code copied',
        description: 'Generated Python code has been copied to clipboard',
        status: 'success',
        duration: 2000,
        isClosable: true,
      });
    }
  };

  const handleDownloadCode = () => {
    if (pythonCode) {
      const blob = new Blob([pythonCode], { type: 'text/x-python' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${workflowName || 'workflow'}_agent.py`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      toast({
        title: 'Code downloaded',
        description: 'Generated Python code has been downloaded',
        status: 'success',
        duration: 2000,
        isClosable: true,
      });
    }
  };

  return (
    <Box
      bg="white"
      borderRadius="lg"
      p={6}
      mb={4}
      mx={4}
      boxShadow="md"
      borderWidth="1px"
      borderColor="ocean.500"
    >
      <VStack align="stretch" spacing={4}>
        {/* Header */}
        <HStack justify="space-between">
          <HStack spacing={3}>
            <Text fontSize="lg" fontWeight="semibold" color="gray.900">
              Execution Details
            </Text>
            <Badge
              px={3}
              py={1}
              borderRadius="md"
              bg="green.600"
              color="white"
              fontSize="sm"
              boxShadow="sm"
            >
              ✓ Completed
            </Badge>
          </HStack>
          {pythonCode && (
            <HStack spacing={2}>
              <Button size="sm" variant="outline" colorScheme="blue" onClick={handleCopyCode}>
                Copy Code
              </Button>
              <Button size="sm" variant="outline" colorScheme="blue" onClick={handleDownloadCode}>
                Download
              </Button>
            </HStack>
          )}
        </HStack>

        <Divider />

        {/* Accordion Sections */}
        <Accordion allowMultiple defaultIndex={[0, 1]}>
          {/* Parameters Section */}
          {collectedParameters && Object.keys(collectedParameters).length > 0 && (
            <AccordionItem border="none">
              <h2>
                <AccordionButton
                  _hover={{ bg: 'sand.50' }}
                  borderRadius="md"
                  py={3}
                  color="gray.900"
                >
                  <Box flex="1" textAlign="left">
                    <Text fontWeight="medium" color="gray.900">
                      Input Parameters
                    </Text>
                  </Box>
                  <AccordionIcon />
                </AccordionButton>
              </h2>
              <AccordionPanel pb={4}>
                <Table size="sm" variant="simple">
                  <Thead>
                    <Tr>
                      <Th color="gray.900" borderColor="gray.700">
                        Parameter
                      </Th>
                      <Th color="gray.900" borderColor="gray.700">
                        Value
                      </Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {Object.entries(collectedParameters).map(([key, value]) => (
                      <Tr key={key} borderColor="gray.200">
                        <Td fontWeight="semibold" color="gray.900" borderColor="gray.200">
                          <Code fontSize="sm" color="gray.900" bg="gray.50">
                            {key}
                          </Code>
                        </Td>
                        <Td borderColor="gray.200">
                          <Text fontSize="sm" color="gray.900">
                            {formatValue(value)}
                          </Text>
                        </Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              </AccordionPanel>
            </AccordionItem>
          )}

          {/* Generated Code Section */}
          {pythonCode && (
            <AccordionItem border="none">
              <h2>
                <AccordionButton
                  _hover={{ bg: 'sand.50' }}
                  borderRadius="md"
                  py={3}
                >
                  <Box flex="1" textAlign="left">
                    <Text fontWeight="medium" color="gray.700">
                      Generated Python Code
                    </Text>
                  </Box>
                  <AccordionIcon />
                </AccordionButton>
              </h2>
              <AccordionPanel pb={4}>
                <Box
                  borderRadius="md"
                  overflow="hidden"
                  borderWidth="1px"
                  borderColor="gray.200"
                >
                  <SyntaxHighlighter
                    language="python"
                    style={vscDarkPlus}
                    customStyle={{
                      margin: 0,
                      borderRadius: '0.375rem',
                      fontSize: '0.875rem',
                      maxHeight: '400px',
                    }}
                    showLineNumbers
                  >
                    {pythonCode}
                  </SyntaxHighlighter>
                </Box>
              </AccordionPanel>
            </AccordionItem>
          )}

          {/* Results Section */}
          <AccordionItem border="none">
            <h2>
              <AccordionButton
                _hover={{ bg: 'sand.50' }}
                borderRadius="md"
                py={3}
              >
                <Box flex="1" textAlign="left">
                  <Text fontWeight="medium" color="gray.700">
                    Execution Results
                  </Text>
                </Box>
                <AccordionIcon />
              </AccordionButton>
            </h2>
            <AccordionPanel pb={4}>
              <Box
                bg="gray.50"
                p={4}
                borderRadius="md"
                fontFamily="mono"
                fontSize="sm"
                overflowX="auto"
              >
                <pre>{JSON.stringify(executionResult, null, 2)}</pre>
              </Box>
            </AccordionPanel>
          </AccordionItem>
        </Accordion>
      </VStack>
    </Box>
  );
};

// Helper function to format values for display
function formatValue(value: any): string {
  if (value === null) return 'null';
  if (value === undefined) return 'undefined';
  if (typeof value === 'boolean') return value.toString();
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}
