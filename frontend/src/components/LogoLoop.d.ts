import { ReactNode } from "react";

export interface LogoLoopLogo {
  src?: string;
  srcSet?: string;
  sizes?: string;
  width?: number;
  height?: number;
  alt?: string;
  title?: string;
  href?: string;
  node?: ReactNode;
  ariaLabel?: string;
}

export interface LogoLoopProps {
  logos: LogoLoopLogo[];
  speed?: number;
  direction?: "left" | "right" | "up" | "down";
  width?: string | number;
  logoHeight?: number;
  gap?: number;
  pauseOnHover?: boolean;
  hoverSpeed?: number;
  fadeOut?: boolean;
  fadeOutColor?: string;
  scaleOnHover?: boolean;
  renderItem?: (item: LogoLoopLogo, key: string) => ReactNode;
  ariaLabel?: string;
  className?: string;
  style?: React.CSSProperties;
}

declare const LogoLoop: React.FC<LogoLoopProps>;
export default LogoLoop;
