import Link from "next/link";
import type { ComponentPropsWithoutRef, ReactNode } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost";
type ButtonSize = "sm" | "md" | "lg";

type SharedProps = {
  variant?: ButtonVariant;
  size?: ButtonSize;
  fullWidth?: boolean;
  className?: string;
  children: ReactNode;
};

type ButtonElementProps = SharedProps &
  Omit<ComponentPropsWithoutRef<"button">, keyof SharedProps> & {
    href?: undefined;
  };

type LinkButtonProps = SharedProps &
  Omit<ComponentPropsWithoutRef<typeof Link>, keyof SharedProps> & {
    href: string;
  };

export type ButtonProps = ButtonElementProps | LinkButtonProps;

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "bg-brand-600 text-white hover:bg-brand-700 border border-transparent shadow-sm",
  secondary:
    "bg-white text-brand-700 hover:bg-brand-50 border border-brand-200 shadow-sm",
  ghost: "bg-transparent text-brand-700 hover:bg-brand-50 border border-transparent",
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: "px-3 py-1.5 text-sm",
  md: "px-4 py-2 text-sm",
  lg: "px-5 py-3 text-base",
};

const baseClasses =
  "inline-flex items-center justify-center rounded-lg font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-60";

function buildClassName({
  variant = "primary",
  size = "md",
  fullWidth = false,
  className = "",
}: SharedProps): string {
  return [
    baseClasses,
    variantClasses[variant],
    sizeClasses[size],
    fullWidth ? "w-full" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");
}

function omitSharedProps<T extends ButtonProps>(
  props: T,
): Omit<T, keyof SharedProps> & { children: ReactNode } {
  const nextProps = { ...props } as T & Record<string, unknown>;
  delete nextProps.variant;
  delete nextProps.size;
  delete nextProps.fullWidth;
  delete nextProps.className;
  return nextProps;
}

export function Button(props: ButtonProps) {
  const classes = buildClassName(props);

  if ("href" in props && props.href) {
    const { href, children, ...linkProps } = omitSharedProps(props);

    return (
      <Link href={href} className={classes} {...linkProps}>
        {children}
      </Link>
    );
  }

  const buttonProps = props as ButtonElementProps;
  const { children, type = "button", ...rest } = omitSharedProps(buttonProps);

  return (
    <button className={classes} type={type} {...rest}>
      {children}
    </button>
  );
}
