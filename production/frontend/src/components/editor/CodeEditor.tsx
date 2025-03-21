import React, { useEffect, useImperativeHandle, useRef } from 'react';
import * as monaco from 'monaco-editor';
import styles from './CodeEditor.module.scss';
import { getEditorSuggestions } from './utils';

interface CodeEditorProps {
  value: string;
  onChange?: (value: string) => void;
  readOnly?: boolean;
  height?: string | number;
  width?: string | number;
}

const defaultOptions: monaco.editor.IStandaloneEditorConstructionOptions = {
  language: 'plaintext',
  codeLens: false,
  contextmenu: false,
  copyWithSyntaxHighlighting: false,
  fixedOverflowWidgets: true,
  folding: false,
  fontFamily: 'Fira Code, monospace, helvetica, Arial, sans-serif',
  fontLigatures: true,
  lineNumbersMinChars: 3,
  lineNumbers: 'off',
  links: false,
  quickSuggestions: true,
  renderFinalNewline: 'off',
  renderLineHighlight: 'none',
  roundedSelection: false,
  scrollBeyondLastLine: false,
  snippetSuggestions: 'none',
  suggestFontSize: 12,
  suggestLineHeight: 26,
  wordBasedSuggestions: 'currentDocument',
  wordWrap: 'on',
  suggest: {
    shareSuggestSelections: false,
    snippetsPreventQuickSuggestions: false,
    localityBonus: false,
    filterGraceful: false,
  },
  minimap: {
    enabled: false,
  },
  scrollbar: {
    horizontalScrollbarSize: 8,
    horizontalSliderSize: 8,
    useShadows: true,
    verticalScrollbarSize: 8,
    verticalSliderSize: 8,
  },
  padding: {
    top: 5,
    bottom: 5,
  },
  automaticLayout: true,
};

export interface EditorHandler {
  getContent: () => string;
}

const CodeEditor: React.ForwardRefRenderFunction<EditorHandler, CodeEditorProps> = (props, ref) => {
  const { value, onChange, readOnly } = props;
  const internalRef = useRef<HTMLDivElement>(null);
  const [editor, setEditor] = React.useState<monaco.editor.IStandaloneCodeEditor | null>(null);

  useImperativeHandle(ref, () => ({
    getContent: () => {
      return editor?.getValue() || '';
    },
  }))

  useEffect(() => {
    if (!internalRef.current) return;

    const editor = monaco.editor.create(internalRef.current, {
      value,
      ...defaultOptions,
    });
    setEditor(editor);

    editor.onDidChangeModelContent(() => {
      handleChange(editor.getValue());
    });

    return () => {
      editor.dispose();
    };
  }, [value, readOnly]);

  useEffect(() => {
    // register keywords
    monaco.languages.registerCompletionItemProvider('plaintext', {
      provideCompletionItems: (model, position) => {
        const word = model.getWordUntilPosition(position);
        const range = new monaco.Range(
          position.lineNumber,
          word.startColumn,
          position.lineNumber,
          word.endColumn
        );

        return {
          suggestions: getEditorSuggestions(
            monaco.languages.CompletionItemKind.Keyword,
            range,
          ),
        };
      },
    });
  }, []);

  const handleChange = (newValue: string) => {
    if (onChange) {
      onChange(newValue);
    }
  };

  return (
    <div
      className={styles.codeEditorContainer}
      ref={internalRef}
      style={{
        height: props.height,
        width: props.width,
      }}
    ></div>
  );
};

export default React.forwardRef(CodeEditor);
