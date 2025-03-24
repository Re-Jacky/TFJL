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
  quickSuggestions: {
    other: true,
    comments: true,
    strings: true
  },
  renderFinalNewline: 'off',
  renderLineHighlight: 'none',
  roundedSelection: false,
  scrollBeyondLastLine: false,
  snippetSuggestions: 'none',
  suggestFontSize: 12,
  suggestLineHeight: 26,
  wordBasedSuggestions: 'currentDocument',
  wordWrap: 'on',
  wordSeparators: '`~!@#$%^&*()-=+[{]}\\|;:\'\",.<>/?',
  suggest: {
    shareSuggestSelections: false,
    snippetsPreventQuickSuggestions: false,
    localityBonus: false,
    filterGraceful: false,
    showWords: true,
    insertMode: 'insert'
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

const CodeEditor: React.ForwardRefRenderFunction<
  EditorHandler,
  CodeEditorProps
> = (props, ref) => {
  const { value, onChange, readOnly } = props;
  const internalRef = useRef<HTMLDivElement>(null);
  const [editor, setEditor] =
    React.useState<monaco.editor.IStandaloneCodeEditor | null>(null);

  useImperativeHandle(ref, () => ({
    getContent: () => {
      return editor?.getValue() || '';
    },
  }));

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
    // Configure tokenizer for Chinese text handling
    // This defines how different parts of the text should be highlighted
    monaco.languages.setMonarchTokensProvider('plaintext', {
      tokenizer: {
        root: [
          // Match Chinese punctuation marks
          [/[。,，]/, 'delimiter.chinese'],
          // Match Chinese characters (Unicode range: 4E00-9FFF)
          [/[\u4E00-\u9FFF]+/, 'identifier.chinese'],
          // Match whitespace
          [/\s+/, 'white'],
        ],
      },
      includeLF: true, // Include line feeds in tokenization
      unicode: true    // Enable Unicode support
    });

    // Register auto-completion provider for Chinese text
    // This enables suggestions when typing Chinese characters
    monaco.languages.registerCompletionItemProvider('plaintext', {
      // Trigger completion on Chinese characters and opening brackets
      triggerCharacters: ['[', '\u4e00-\u9fa5'],
      provideCompletionItems: (model, position) => {
        const wordInfo = model.getWordUntilPosition(position);
        
        // Define the range for replacing the current word with suggestion
        const range = new monaco.Range(
          position.lineNumber,
          wordInfo.startColumn,
          position.lineNumber,
          wordInfo.endColumn
        );

        return {
          suggestions: getEditorSuggestions(
            monaco.languages.CompletionItemKind.Keyword,
            range
          ),
        };
      },
    });

    // Configure word pattern to properly handle Chinese characters
    // This affects word-based operations like double-click selection
    monaco.languages.setLanguageConfiguration('plaintext', {
      // Match either continuous Chinese characters or Latin letters
      wordPattern: /[\u4e00-\u9fa5]+|[a-zA-Z]+/g
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
