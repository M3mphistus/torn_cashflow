import type { ButtonHTMLAttributes } from 'react';

type Variant = 'default' | 'primary' | 'danger';

export default function Button({
  variant = 'default',
  className = '',
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  const variantClass = variant === 'default' ? '' : variant;
  return <button className={`${variantClass} ${className}`.trim()} {...rest} />;
}
