'use client';

import React, { useState, useCallback } from 'react';

interface FormItemProps {
  name?: string;
  label?: React.ReactNode;
  children: React.ReactNode;
  rules?: { required?: boolean; type?: string; message?: string; min?: number; max?: number; pattern?: RegExp }[];
  extra?: React.ReactNode;
  valuePropName?: string;
  style?: React.CSSProperties;
}

interface LFormProps {
  children: React.ReactNode;
  form?: { resetFields?: () => void };
  layout?: 'horizontal' | 'vertical' | 'inline';
  initialValues?: Record<string, unknown>;
  onFinish?: (values: Record<string, unknown>) => void;
  size?: 'small' | 'middle' | 'large';
  style?: React.CSSProperties;
}

interface LFormHandle {
  validateFields: () => Promise<Record<string, unknown>>;
  setFieldsValue: (values: Record<string, unknown>) => void;
  resetFields: () => void;
}

const FormContext = React.createContext<{
  values: Record<string, unknown>;
  errors: Record<string, string>;
  setFieldValue: (name: string, value: unknown) => void;
  setFieldError: (name: string, error: string) => void;
  clearFieldError: (name: string) => void;
  layout: 'horizontal' | 'vertical' | 'inline';
  size: 'small' | 'middle' | 'large';
}>({
  values: {}, errors: {},
  setFieldValue: () => {}, setFieldError: () => {}, clearFieldError: () => {},
  layout: 'vertical', size: 'middle',
});

function LFormItem({ name, label, children, rules, extra, valuePropName, style }: FormItemProps) {
  const ctx = React.useContext(FormContext);
  const child = React.Children.only(children) as React.ReactElement<{ onChange?: (...args: unknown[]) => void }>;

  const handleChange = useCallback((...args: unknown[]) => {
    if (name && child.props.onChange) {
      const first = args[0] as { target?: HTMLInputElement; checked?: boolean };
      const value = valuePropName === 'checked' ? first?.checked ?? args[0] : (first?.target as HTMLInputElement)?.value ?? args[0];
      ctx.setFieldValue(name, value);
      ctx.clearFieldError(name);
    }
  }, [name, child.props.onChange, valuePropName, ctx]);

  const childProps: Record<string, unknown> = {};
  if (name) {
    if (valuePropName === 'checked') {
      childProps.checked = Boolean(ctx.values[name]);
    } else {
      childProps.value = ctx.values[name] ?? '';
    }
  }
  childProps.onChange = handleChange;
  const enhancedChild = React.cloneElement(child, childProps);

  const error = name ? ctx.errors[name] : undefined;
  const isVertical = ctx.layout === 'vertical';
  const labelSize = ctx.size === 'small' ? 12 : ctx.size === 'large' ? 15 : 13;

  return (
    <div style={{ marginBottom: ctx.size === 'small' ? 8 : 16, ...style }}>
      {label && (
        <label style={{ display: 'block', marginBottom: isVertical ? 4 : 0, fontSize: labelSize, fontWeight: 500, color: '#333' }}>
          {label}
        </label>
      )}
      <div style={{ display: isVertical ? 'block' : 'flex', alignItems: 'center', gap: 8 }}>
        {enhancedChild}
      </div>
      {error && <div style={{ fontSize: 12, color: '#ef4444', marginTop: 2 }}>{error}</div>}
      {extra && !error && <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>{extra}</div>}
    </div>
  );
}

export function useLForm() {
  const ref = React.useRef<LFormHandle>(null);
  return [{
    validateFields: () => ref.current?.validateFields() ?? Promise.resolve({}),
    resetFields: () => ref.current?.resetFields(),
    setFieldsValue: (vals: Record<string, unknown>) => ref.current?.setFieldsValue(vals),
  }, ref] as const;
}

export const LForm = Object.assign(
  React.forwardRef<LFormHandle, LFormProps>(function LForm(
    { children, layout = 'vertical', initialValues = {}, onFinish, size = 'middle', style }: LFormProps,
    ref
  ) {
    const [values, setValues] = useState<Record<string, unknown>>(initialValues);
    const [errors, setErrors] = useState<Record<string, string>>({});

    const setFieldValue = useCallback((name: string, value: unknown) => {
      setValues(prev => ({ ...prev, [name]: value }));
    }, []);

    const setFieldError = useCallback((name: string, error: string) => {
      setErrors(prev => ({ ...prev, [name]: error }));
    }, []);

    const clearFieldError = useCallback((name: string) => {
      setErrors(prev => {
        const next = { ...prev };
        delete next[name];
        return next;
      });
    }, []);

    React.useImperativeHandle(ref, () => ({
      validateFields: async () => {
        const collected: Record<string, unknown> = {};
        const newErrors: Record<string, string> = {};
        // Collect all known values
        Object.assign(collected, values);
        if (Object.keys(newErrors).length > 0) {
          setErrors(newErrors);
          throw new Error('Validation failed');
        }
        return collected;
      },
      setFieldsValue: (vals: Record<string, unknown>) => setValues(prev => ({ ...prev, ...vals })),
      resetFields: () => { setValues(initialValues); setErrors({}); },
    }));

    const handleSubmit = (e: React.FormEvent) => {
      e.preventDefault();
      if (onFinish) onFinish(values);
    };

    const labelSizeVal = size === 'small' ? 12 : size === 'large' ? 14 : 13;

    return (
      <FormContext.Provider value={{ values, errors, setFieldValue, setFieldError, clearFieldError, layout, size }}>
        <form onSubmit={handleSubmit} style={{ ...style }}>
          {children}
        </form>
      </FormContext.Provider>
    );
  }),
  { Item: LFormItem }
);