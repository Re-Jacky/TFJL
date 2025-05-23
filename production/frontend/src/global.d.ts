// make the file treated as a module by ts
export {};

declare module '*.module.scss' {
  const content: { [className: string]: string };
  export default content;
}

declare global {
  interface Window {
    nodeAPI: {
      restartServer: () => void;
    };
  }
}