/**
 * Parameter collection drawer component
 */

import React, { useState, useEffect } from 'react';
import {
  Drawer,
  DrawerBody,
  DrawerFooter,
  DrawerHeader,
  DrawerOverlay,
  DrawerContent,
  DrawerCloseButton,
  Button,
  FormControl,
  FormLabel,
  FormHelperText,
  Input,
  Textarea,
  Select,
  VStack,
  Text,
  Badge,
} from '@chakra-ui/react';
import type { WorkflowParameter } from '../../services/types';

interface ParameterDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  parameters: WorkflowParameter[];
  pendingParameters: string[];
  onSubmit: (values: Record<string, any>) => void;
}

export const ParameterDrawer: React.FC<ParameterDrawerProps> = ({
  isOpen,
  onClose,
  parameters,
  pendingParameters,
  onSubmit,
}) => {
  const [values, setValues] = useState<Record<string, any>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Initialize values when parameters change
  useEffect(() => {
    const initialValues: Record<string, any> = {};
    parameters.forEach((param) => {
      if (param.default !== undefined) {
        initialValues[param.name] = param.default;
      }
    });
    setValues(initialValues);
  }, [parameters]);

  const handleChange = (name: string, value: any) => {
    setValues((prev) => ({ ...prev, [name]: value }));
    // Clear error when user types
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: '' }));
    }
  };

  const handleSubmit = () => {
    console.log('[ParameterDrawer] Submit clicked');
    console.log('[ParameterDrawer] Current values:', values);
    console.log('[ParameterDrawer] Pending parameters:', pendingParameters);

    // Validate returns true if valid, but setErrors is async
    // So we need to calculate errors inline
    const validationErrors: Record<string, string> = {};

    pendingParameters.forEach((paramName) => {
      const param = parameters.find((p) => p.name === paramName);
      if (!param) return;

      const value = values[paramName];

      // Check required
      if (param.required && !value) {
        validationErrors[paramName] = 'This field is required';
      }
    });

    if (Object.keys(validationErrors).length > 0) {
      console.log('[ParameterDrawer] Validation failed:', validationErrors);
      setErrors(validationErrors);
      return;
    }

    const submittedValues: Record<string, any> = {};
    pendingParameters.forEach((paramName) => {
      if (values[paramName] !== undefined) {
        submittedValues[paramName] = values[paramName];
      }
    });

    console.log('[ParameterDrawer] Submitting values:', submittedValues);
    onSubmit(submittedValues);
    setValues({});
    setErrors({});
  };

  const renderField = (param: WorkflowParameter) => {
    const isPending = pendingParameters.includes(param.name);
    const value = values[param.name] || '';
    const error = errors[param.name];

    if (!isPending) return null;

    return (
      <FormControl key={param.name} isInvalid={!!error}>
        <FormLabel>
          {param.name}
          {param.required && (
            <Badge ml={2} colorScheme="orange" fontSize="xs">
              Required
            </Badge>
          )}
        </FormLabel>

        {renderInput(param, value, (v) => handleChange(param.name, v))}

        {param.description && (
          <FormHelperText>{param.description}</FormHelperText>
        )}

        {error && (
          <Text color="red.500" fontSize="sm" mt={1}>
            {error}
          </Text>
        )}
      </FormControl>
    );
  };

  return (
    <Drawer isOpen={isOpen} placement="right" onClose={onClose} size="md">
      <DrawerOverlay />
      <DrawerContent>
        <DrawerCloseButton />
        <DrawerHeader borderBottomWidth="1px">
          Provide Information
        </DrawerHeader>

        <DrawerBody>
          <VStack spacing={4} mt={4}>
            <Text fontSize="sm" color="gray.600">
              Please provide the following information to continue:
            </Text>

            {parameters.map(renderField)}

            {pendingParameters.length === 0 && (
              <Text color="gray.500">No parameters needed.</Text>
            )}
          </VStack>
        </DrawerBody>

        <DrawerFooter borderTopWidth="1px">
          <Button variant="outline" mr={3} onClick={onClose}>
            Cancel
          </Button>
          <Button
            colorScheme="blue"
            onClick={handleSubmit}
            isDisabled={pendingParameters.length === 0}
          >
            Submit
          </Button>
        </DrawerFooter>
      </DrawerContent>
    </Drawer>
  );
};

function renderInput(
  param: WorkflowParameter,
  value: any,
  onChange: (value: any) => void
) {
  const type = param.type.toLowerCase();

  // Special handling for specific types
  if (type === 'boolean') {
    return (
      <Select
        value={String(value)}
        onChange={(e) => onChange(e.target.value === 'true')}
        placeholder="Select..."
      >
        <option value="true">Yes</option>
        <option value="false">No</option>
      </Select>
    );
  }

  if (type === 'text' || type.includes('description')) {
    return (
      <Textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={`Enter ${param.name}...`}
        rows={3}
      />
    );
  }

  if (type === 'date') {
    return (
      <Input
        type="date"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  }

  if (type === 'email') {
    return (
      <Input
        type="email"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="email@example.com"
      />
    );
  }

  if (type === 'number' || type === 'float' || type === 'integer') {
    return (
      <Input
        type="number"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="0"
      />
    );
  }

  // Default text input
  return (
    <Input
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={`Enter ${param.name}...`}
    />
  );
}
