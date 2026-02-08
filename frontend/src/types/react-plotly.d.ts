declare module 'react-plotly.js' {
  import { Component } from 'react';
  import { PlotParams } from 'plotly.js';

  export interface PlotProps extends Partial<PlotParams> {
    data: Partial<PlotParams['data']>;
    layout?: Partial<PlotParams['layout']>;
    config?: Partial<PlotParams['config']>;
    frames?: Partial<PlotParams['frames']>;
    onClick?: (event: any) => void;
    onHover?: (event: any) => void;
    onUnhover?: (event: any) => void;
    onSelected?: (event: any) => void;
    onRelayout?: (event: any) => void;
    onUpdate?: (figure: any, graphDiv: any) => void;
    onInitialized?: (figure: any, graphDiv: any) => void;
    onPurge?: (figure: any, graphDiv: any) => void;
    onError?: (err: any) => void;
    useResizeHandler?: boolean;
    style?: React.CSSProperties;
    className?: string;
    divId?: string;
    revision?: number;
    onClickAnnotation?: (event: any) => void;
    onLegendClick?: (event: any) => void;
    onLegendDoubleClick?: (event: any) => void;
    onSliderChange?: (event: any) => void;
    onBeforeExport?: () => void;
    onAfterExport?: () => void;
    onAnimated?: () => void;
    onAnimatingFrame?: (event: any) => void;
    onAnimationInterrupted?: () => void;
    onAutoSize?: () => void;
    onButtonClicked?: (event: any) => void;
    onDeselect?: () => void;
    onDoubleClick?: () => void;
    onFramework?: () => void;
    onRedraw?: () => void;
    onRestyle?: (data: any) => void;
    onWebGlContextLost?: () => void;
    debug?: boolean;
  }

  export default class Plot extends Component<PlotProps> {}
}
