import type { ReactNode } from "react";

type PageContainerProps = {
  children: ReactNode;
  as?: "div" | "main" | "section";
  className?: string;
  narrow?: boolean;
};

export function PageContainer({
  children,
  as: Component = "div",
  className = "",
  narrow = false,
}: PageContainerProps) {
  return (
    <Component
      className={[
        "mx-auto w-full min-w-0 max-w-full px-4 sm:px-6 lg:px-8",
        narrow ? "max-w-xl" : "max-w-6xl",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {children}
    </Component>
  );
}
